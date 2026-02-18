"""Cross-encoder reranker for improving retrieval quality."""

import logging
import threading
from sentence_transformers import CrossEncoder
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for retrieved chunks."""

    def __init__(self, model_name: str):
        """
        Initialize reranker with cross-encoder model.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        logger.info(f"Loading reranker model: {model_name}")
        self.model = CrossEncoder(model_name)
        self._lock = threading.Lock()
        logger.info("Reranker model loaded successfully")

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks using cross-encoder.

        Returns ALL scored candidates sorted by relevance (no truncation).
        The caller is responsible for applying any cutoff.

        Args:
            query: User question
            chunks: Retrieved chunks from first-stage retrieval

        Returns:
            All reranked chunks with updated scores (sorted by relevance)
        """
        if not chunks:
            return []

        # Extract text from chunks
        chunk_texts = []
        for chunk in chunks:
            if "payload" in chunk and "text" in chunk["payload"]:
                chunk_texts.append(chunk["payload"]["text"])
            elif "text" in chunk:
                chunk_texts.append(chunk["text"])
            else:
                chunk_texts.append(str(chunk))

        # Create (query, document) pairs for cross-encoder
        pairs = [(query, text) for text in chunk_texts]

        # Get reranking scores from cross-encoder
        with self._lock:
            scores = self.model.predict(pairs)

        # Combine chunks with their rerank scores
        reranked = []
        for chunk, score in zip(chunks, scores):
            reranked_chunk = chunk.copy()
            reranked_chunk["rerank_score"] = float(score)
            if "score" in chunk:
                reranked_chunk["retrieval_score"] = chunk["score"]
            reranked_chunk["score"] = float(score)
            reranked.append(reranked_chunk)

        # Sort by rerank score (descending)
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        return reranked

    def rerank_with_position_blending(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        blend_strategy: str
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks with position-aware score blending.

        Returns ALL scored candidates sorted by blended score (no truncation).
        The caller is responsible for applying any cutoff.

        Args:
            query: User question
            chunks: Retrieved chunks from first-stage retrieval
            blend_strategy: "position_aware" or "replace" (default reranking)

        Returns:
            All reranked chunks with blended scores (sorted by relevance)
        """
        if not chunks:
            return []

        # If replace strategy, use standard reranking
        if blend_strategy == "replace":
            return self.rerank(query, chunks)

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
        with self._lock:
            rerank_scores = self.model.predict(pairs)

        # Apply position-aware blending
        reranked = []
        for rank, (chunk, rerank_score) in enumerate(zip(chunks, rerank_scores), start=1):
            reranked_chunk = chunk.copy()

            # Get original retrieval score
            retrieval_score = chunk.get("score", 0.5)

            # Determine blend weights based on position
            if rank <= 3:
                retrieval_weight = 0.75
                rerank_weight = 0.25
            elif rank <= 10:
                retrieval_weight = 0.5
                rerank_weight = 0.5
            else:
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

        return reranked
