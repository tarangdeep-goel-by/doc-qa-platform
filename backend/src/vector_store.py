"""Vector store wrapper for Qdrant."""

from typing import List, Dict, Any, Optional
import uuid
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny
)
from src.bm25_index import BM25Index


class VectorStore:
    """Wrapper for Qdrant vector database operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "documents",
        vector_size: int = 384
    ):
        """
        Initialize Qdrant client and collection.

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Name of collection to use
            vector_size: Dimension of vectors
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Connect to Qdrant
        self.client = QdrantClient(host=host, port=port)

        # Initialize collection
        self._init_collection()

        # Initialize BM25 index
        self.bm25_index = BM25Index()
        self.bm25_index.load_cache()  # Try to load cached index

    def _init_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            print(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"Collection created: {self.collection_name}")
        else:
            print(f"Collection already exists: {self.collection_name}")

    def add_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray
    ) -> int:
        """
        Add document chunks with embeddings to Qdrant.

        Args:
            chunks: List of chunk payloads
            embeddings: Numpy array of embeddings

        Returns:
            Number of chunks added
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload=chunk
            )
            points.append(point)

        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        # Rebuild BM25 index with new chunks
        self.rebuild_bm25_index()

        return len(points)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            doc_ids: Optional list of document IDs to filter by

        Returns:
            List of search results with scores
        """
        # Build filter if doc_ids specified
        query_filter = None
        if doc_ids:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchAny(any=doc_ids)
                    )
                ]
            )

        # Search (using query_points for newer qdrant-client)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=top_k,
            query_filter=query_filter
        ).points

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            })

        return formatted_results

    def delete_document(self, doc_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            doc_id: Document ID

        Returns:
            Number of chunks deleted
        """
        # Delete points matching doc_id
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        )

        # Rebuild BM25 index after deletion
        self.rebuild_bm25_index()

        return 0  # Qdrant doesn't return count

    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.points_count,
            "vector_size": self.vector_size
        }

    def check_connection(self) -> bool:
        """Check if Qdrant is accessible."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def rebuild_bm25_index(self):
        """
        Rebuild BM25 index from all chunks in Qdrant.
        Should be called after adding or deleting documents.
        """
        # Fetch all points from Qdrant
        # Note: This uses scroll which is efficient for large datasets
        all_chunks = []
        offset = None
        limit = 100

        while True:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False  # We don't need vectors for BM25
            )

            points, offset = result

            if not points:
                break

            # Extract payloads
            for point in points:
                all_chunks.append(point.payload)

            if offset is None:
                break

        print(f"Rebuilding BM25 index with {len(all_chunks)} chunks")
        self.bm25_index.build_index(all_chunks)

    def hybrid_search(
        self,
        query_vector: np.ndarray,
        query_text: str,
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and BM25 keyword matching.

        Args:
            query_vector: Query embedding
            query_text: Original query text for BM25
            top_k: Number of final results to return
            doc_ids: Optional list of document IDs to filter by
            alpha: Weight for vector vs BM25 (0=all BM25, 1=all vector, 0.5=balanced)

        Returns:
            List of search results with combined scores
        """
        # Get more candidates from both methods
        candidates_k = min(top_k * 4, 20)  # Get 4x candidates or max 20

        # Vector search
        vector_results = self.search(
            query_vector=query_vector,
            top_k=candidates_k,
            doc_ids=doc_ids
        )

        # BM25 search
        bm25_results = self.bm25_index.search(
            query=query_text,
            top_k=candidates_k,
            doc_ids=doc_ids
        )

        # Normalize scores
        vector_scores = self._normalize_scores([r["score"] for r in vector_results])
        bm25_scores = self._normalize_scores([r["score"] for r in bm25_results])

        # Combine scores
        combined = {}

        # Add vector results
        for i, result in enumerate(vector_results):
            chunk_id = result["id"]
            combined[chunk_id] = {
                "result": result,
                "score": alpha * vector_scores[i]
            }

        # Add BM25 results
        for i, result in enumerate(bm25_results):
            # BM25 results use chunk data directly
            chunk_text = result["chunk"]["text"]

            # Find matching vector result by text (since we don't have IDs from BM25)
            matching_id = None
            for vr in vector_results:
                if vr["payload"].get("text") == chunk_text:
                    matching_id = vr["id"]
                    break

            if matching_id:
                # Add BM25 score to existing entry
                combined[matching_id]["score"] += (1 - alpha) * bm25_scores[i]
            else:
                # New result from BM25 only
                # Create a pseudo-result (this shouldn't happen often if both indices are synced)
                pass

        # Sort by combined score
        sorted_results = sorted(
            combined.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # Return top k with original format
        final_results = []
        for chunk_id, data in sorted_results[:top_k]:
            result = data["result"]
            result["score"] = data["score"]  # Update with combined score
            final_results.append(result)

        return final_results

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize scores to 0-1 range using min-max normalization.

        Args:
            scores: List of raw scores

        Returns:
            List of normalized scores
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            # All scores are the same
            return [1.0] * len(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]
