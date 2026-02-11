"""BM25-based document routing for automatic document selection."""

import logging
from collections import defaultdict
from typing import List

from .bm25_index import BM25Index, tokenize

logger = logging.getLogger(__name__)


def route_query(
    question: str,
    bm25_index: BM25Index,
    max_docs: int = 5,
    min_score_ratio: float = 0.45,
) -> List[str]:
    """
    Route a question to the most relevant documents using BM25 chunk scores.

    Scores all chunks against the question, aggregates by doc_id,
    and returns top docs above a relative threshold.

    Args:
        question: User's question
        bm25_index: Populated BM25 index
        max_docs: Maximum number of documents to return
        min_score_ratio: Minimum score as ratio of top doc's score (0-1)

    Returns:
        List of doc_ids, or empty list if no match (caller falls back to all docs)
    """
    if not bm25_index.index or not bm25_index.chunks:
        return []

    tokens = tokenize(question)
    if not tokens:
        return []

    scores = bm25_index.index.get_scores(tokens)

    # Aggregate scores by doc_id
    doc_scores: dict[str, float] = defaultdict(float)
    for i, score in enumerate(scores):
        if score > 0:
            doc_scores[bm25_index.doc_ids[i]] += score

    if not doc_scores:
        return []

    # Sort by score descending
    ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    top_score = ranked[0][1]

    # Relative threshold: keep docs with >= min_score_ratio of top doc's score
    threshold = top_score * min_score_ratio
    result = [doc_id for doc_id, score in ranked if score >= threshold]

    # Cap at max_docs
    result = result[:max_docs]

    logger.info(
        f"Doc routing: question='{question[:80]}' → {len(result)} docs "
        f"(top_score={top_score:.2f}, threshold={threshold:.2f})"
    )

    return result
