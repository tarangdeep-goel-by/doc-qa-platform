"""Vector store wrapper for Qdrant."""

from typing import List, Dict, Any, Optional
import uuid
import numpy as np
from collections import defaultdict
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
        host: str,
        port: int,
        collection_name: str,
        vector_size: int,
        bm25_cache_dir: str
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
        self.bm25_index = BM25Index(cache_dir=bm25_cache_dir)
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
        top_k: int,
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
        all_chunks = []
        point_ids = []
        offset = None
        limit = 100

        while True:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points, offset = result

            if not points:
                break

            for point in points:
                all_chunks.append(point.payload)
                point_ids.append(str(point.id))

            if offset is None:
                break

        print(f"Rebuilding BM25 index with {len(all_chunks)} chunks")
        self.bm25_index.build_index(all_chunks, point_ids=point_ids)

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60,
        top_bonuses: Dict[int, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).

        RRF is more robust than weighted averaging for combining different
        ranking methods with different score distributions.

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            k: RRF constant (typically 60)
            top_bonuses: Optional position bonuses {rank: bonus_score}

        Returns:
            List of fused results sorted by RRF score
        """
        if top_bonuses is None:
            top_bonuses = {1: 0.05, 2: 0.02, 3: 0.02}

        chunk_scores = defaultdict(lambda: {'score': 0.0, 'result': None})

        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["id"]
            rrf_score = 1.0 / (k + rank)

            # Add position bonus for top results
            if rank in top_bonuses:
                rrf_score += top_bonuses[rank]

            chunk_scores[chunk_id]['score'] += rrf_score
            chunk_scores[chunk_id]['result'] = result

        # Process BM25 results — use point_id for O(1) matching
        for rank, result in enumerate(bm25_results, start=1):
            matching_id = result.get("point_id")

            if matching_id and matching_id in chunk_scores:
                # Add RRF score to existing chunk
                rrf_score = 1.0 / (k + rank)
                if rank in top_bonuses:
                    rrf_score += top_bonuses[rank]

                chunk_scores[matching_id]['score'] += rrf_score
            # If not found in vector results, skip (shouldn't happen if indices synced)

        # Sort by RRF score
        fused_results = []
        for chunk_id, data in chunk_scores.items():
            if data['result'] is not None:
                result = data['result'].copy()
                result['score'] = data['score']
                fused_results.append(result)

        return sorted(fused_results, key=lambda x: x['score'], reverse=True)

    def hybrid_search(
        self,
        query_vector: np.ndarray,
        query_text: str,
        top_k: int,
        doc_ids: Optional[List[str]] = None,
        alpha: float = 0.5,
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

        # Reciprocal Rank Fusion (RRF)
        fused_results = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            k=60
        )

        # Normalize RRF scores to 0-1 range (for consistency with min_score thresholds)
        if fused_results and len(fused_results) > 1:
            scores = [r["score"] for r in fused_results]
            min_score = min(scores)
            max_score = max(scores)

            if max_score > min_score:
                for i, result in enumerate(fused_results):
                    result["score"] = (result["score"] - min_score) / (max_score - min_score)
            else:
                # All scores are the same
                for result in fused_results:
                    result["score"] = 1.0

        return fused_results[:top_k]

    def multi_query_hybrid_search(
        self,
        query_variants: List[str],
        query_embeddings: List[np.ndarray],
        query_weights: List[float],
        top_k: int,
        doc_ids: Optional[List[str]] = None,
        alpha: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search with multiple query variants and fuse results.

        Args:
            query_variants: List of query text variants
            query_embeddings: List of query embeddings
            query_weights: Weight for each query (e.g., [2.0, 1.0, 1.0] for original + 2 variants)
            top_k: Number of final results to return
            doc_ids: Optional list of document IDs to filter by
            alpha: Weight for vector vs BM25 (0=all BM25, 1=all vector, 0.5=balanced)

        Returns:
            List of search results with fused scores
        """
        # Collect all results from each query variant
        all_results = {}  # chunk_id -> {result, weighted_score}

        for query_text, query_embedding, weight in zip(query_variants, query_embeddings, query_weights):
            # Get results for this variant
            results = self.hybrid_search(
                query_vector=query_embedding,
                query_text=query_text,
                top_k=top_k * 4,  # Get more candidates
                doc_ids=doc_ids,
                alpha=alpha,
            )

            # Add weighted scores
            for result in results:
                chunk_id = result["id"]
                weighted_score = result["score"] * weight

                if chunk_id in all_results:
                    # Sum scores from multiple queries
                    all_results[chunk_id]["score"] += weighted_score
                else:
                    # New chunk
                    all_results[chunk_id] = {
                        "result": result,
                        "score": weighted_score
                    }

        # Sort by fused score
        sorted_results = sorted(
            all_results.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # Extract scores for normalization
        scores = [data["score"] for _, data in sorted_results]

        # Normalize fused scores to 0-1 range (for consistency with min_score thresholds)
        if scores and len(scores) > 1:
            min_score = min(scores)
            max_score = max(scores)
            if max_score > min_score:
                normalized_scores = [(s - min_score) / (max_score - min_score) for s in scores]
            else:
                normalized_scores = [1.0] * len(scores)
        else:
            normalized_scores = scores if scores else []

        # Return top k with original format and normalized scores
        final_results = []
        for i, (chunk_id, data) in enumerate(sorted_results[:top_k]):
            result = data["result"]
            result["score"] = normalized_scores[i] if i < len(normalized_scores) else data["score"]
            final_results.append(result)

        return final_results

