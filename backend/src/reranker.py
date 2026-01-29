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

    def rerank_with_position_blending(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5,
        blend_strategy: str = "position_aware"
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks with position-aware score blending.

        Instead of replacing retrieval scores entirely, this method blends
        retrieval and reranker scores based on position. Top results get
        more weight from retrieval (which already ranked them highly), while
        lower results get more weight from the reranker.

        Args:
            query: User question
            chunks: Retrieved chunks from first-stage retrieval
            top_k: Number of top chunks to return after reranking
            blend_strategy: "position_aware" or "replace" (default reranking)

        Returns:
            Reranked chunks with blended scores (sorted by relevance)
        """
        if not chunks:
            return []

        # If replace strategy, use standard reranking
        if blend_strategy == "replace":
            return self.rerank(query, chunks, top_k)

        # First, get rerank scores for all chunks
        chunk_texts = []
        for chunk in chunks:
            if "payload" in chunk and "text" in chunk["payload"]:
                chunk_texts.append(chunk["payload"]["text"])
            elif "text" in chunk:
                chunk_texts.append(chunk["text"])
            else:
                chunk_texts.append(str(chunk))

        # Get reranking scores
        pairs = [(query, text) for text in chunk_texts]
        rerank_scores = self.model.predict(pairs)

        # Apply position-aware blending
        reranked = []
        for rank, (chunk, rerank_score) in enumerate(zip(chunks, rerank_scores), start=1):
            reranked_chunk = chunk.copy()

            # Get original retrieval score
            retrieval_score = chunk.get("score", 0.5)

            # Determine blend weights based on position
            if rank <= 3:
                # Top 3: Trust retrieval more (75%)
                retrieval_weight = 0.75
                rerank_weight = 0.25
            elif rank <= 10:
                # Ranks 4-10: Equal weight (50/50)
                retrieval_weight = 0.5
                rerank_weight = 0.5
            else:
                # Ranks 11+: Trust reranker more (75%)
                retrieval_weight = 0.25
                rerank_weight = 0.75

            # Compute blended score
            blended_score = (
                retrieval_weight * retrieval_score +
                rerank_weight * float(rerank_score)
            )

            # Store all scores for transparency
            reranked_chunk["retrieval_score"] = retrieval_score
            reranked_chunk["rerank_score"] = float(rerank_score)
            reranked_chunk["blend_weights"] = {
                "retrieval": retrieval_weight,
                "rerank": rerank_weight
            }
            reranked_chunk["score"] = blended_score

            reranked.append(reranked_chunk)

        # Sort by blended score (descending)
        reranked.sort(key=lambda x: x["score"], reverse=True)

        # Return top k
        return reranked[:top_k]
