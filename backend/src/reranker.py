"""Cross-encoder reranker for improving retrieval quality."""

from sentence_transformers import CrossEncoder
from typing import List, Dict, Any


class Reranker:
    """Cross-encoder reranker for retrieved chunks."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker with cross-encoder model.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        print(f"Loading reranker model: {model_name}")
        self.model = CrossEncoder(model_name)
        print(f"Reranker model loaded successfully")

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks using cross-encoder.

        The cross-encoder evaluates how well each chunk answers the specific query,
        providing more accurate relevance scores than bi-encoder similarity alone.

        Args:
            query: User question
            chunks: Retrieved chunks from first-stage retrieval
            top_k: Number of top chunks to return after reranking

        Returns:
            Reranked chunks with updated scores (sorted by relevance)
        """
        if not chunks:
            return []

        # Extract text from chunks
        # Chunks can have different formats (from vector search or hybrid search)
        chunk_texts = []
        for chunk in chunks:
            if "payload" in chunk and "text" in chunk["payload"]:
                chunk_texts.append(chunk["payload"]["text"])
            elif "text" in chunk:
                chunk_texts.append(chunk["text"])
            else:
                # Fallback - try to find text anywhere
                chunk_texts.append(str(chunk))

        # Create (query, document) pairs for cross-encoder
        pairs = [(query, text) for text in chunk_texts]

        # Get reranking scores from cross-encoder
        # These scores represent how well each chunk answers the query
        scores = self.model.predict(pairs)

        # Combine chunks with their rerank scores
        reranked = []
        for chunk, score in zip(chunks, scores):
            # Keep original chunk data and add rerank score
            reranked_chunk = chunk.copy()
            reranked_chunk["rerank_score"] = float(score)
            # Keep original score as "retrieval_score" for comparison
            if "score" in chunk:
                reranked_chunk["retrieval_score"] = chunk["score"]
            # Update main score to rerank score
            reranked_chunk["score"] = float(score)
            reranked.append(reranked_chunk)

        # Sort by rerank score (descending)
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Return top k
        return reranked[:top_k]
