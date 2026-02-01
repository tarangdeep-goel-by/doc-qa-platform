"""Retrieval quality metrics: NDCG@k, MRR, Precision@k, Recall@k."""

import math
from typing import List, Dict, Any, Optional


def _is_relevant(source: Dict[str, Any], expected_sources: List[str]) -> bool:
    """Check if a retrieved source matches any expected source.

    Matches on page number (e.g. "p.22") or document title substring.
    """
    if not expected_sources:
        return True  # No ground truth → can't judge

    page_num = source.get("page_num")
    doc_title = source.get("doc_title", "")
    chunk_text = source.get("chunk_text", "")

    for expected in expected_sources:
        # Match page reference like "p.22"
        if expected.startswith("p."):
            try:
                expected_page = int(expected[2:])
                if page_num == expected_page:
                    return True
            except ValueError:
                pass

        # Match title substring
        if expected.lower() in doc_title.lower():
            return True

        # Match content substring
        if expected.lower() in chunk_text.lower():
            return True

    return False


def precision_at_k(
    sources: List[Dict[str, Any]],
    expected_sources: List[str],
    k: int = 5,
) -> float:
    """Fraction of top-k results that are relevant.

    Returns:
        Float 0-1. Higher is better.
    """
    if not sources or not expected_sources:
        return 0.0

    top_k = sources[:k]
    relevant = sum(1 for s in top_k if _is_relevant(s, expected_sources))
    return relevant / k


def recall_at_k(
    sources: List[Dict[str, Any]],
    expected_sources: List[str],
    k: int = 5,
) -> float:
    """Fraction of all relevant sources found in top-k.

    Returns:
        Float 0-1. Higher is better.
    """
    if not expected_sources:
        return 0.0

    top_k = sources[:k]
    found = set()
    for s in top_k:
        for exp in expected_sources:
            if _is_relevant(s, [exp]):
                found.add(exp)

    return len(found) / len(expected_sources)


def mrr(
    sources: List[Dict[str, Any]],
    expected_sources: List[str],
) -> float:
    """Mean Reciprocal Rank - how high is the first relevant result.

    Returns:
        Float 0-1. Higher is better.
    """
    if not sources or not expected_sources:
        return 0.0

    for i, source in enumerate(sources):
        if _is_relevant(source, expected_sources):
            return 1.0 / (i + 1)

    return 0.0


def ndcg_at_k(
    sources: List[Dict[str, Any]],
    expected_sources: List[str],
    k: int = 5,
) -> float:
    """Normalized Discounted Cumulative Gain at k.

    Measures ranking quality - relevant results should appear higher.

    Returns:
        Float 0-1. Higher is better.
    """
    if not sources or not expected_sources:
        return 0.0

    top_k = sources[:k]

    # Compute DCG - relevance is binary (1 if relevant, 0 if not)
    dcg = 0.0
    for i, source in enumerate(top_k):
        rel = 1.0 if _is_relevant(source, expected_sources) else 0.0
        dcg += rel / math.log2(i + 2)  # +2 because log2(1)=0

    # Compute ideal DCG (all relevant first)
    n_relevant = min(len(expected_sources), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_relevant))

    if idcg == 0:
        return 0.0

    return dcg / idcg


def compute_retrieval_metrics(
    sources: List[Dict[str, Any]],
    expected_sources: List[str],
    k_values: Optional[List[int]] = None,
) -> Dict[str, float]:
    """Compute all retrieval metrics for a single query.

    Args:
        sources: Retrieved sources from the RAG pipeline.
        expected_sources: Ground truth source references (e.g. ["p.22", "p.29"]).
        k_values: List of k values for @k metrics. Default [1, 3, 5, 10].

    Returns:
        Dict of metric_name → value.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    metrics: Dict[str, float] = {}

    metrics["mrr"] = mrr(sources, expected_sources)

    for k in k_values:
        metrics[f"precision@{k}"] = precision_at_k(sources, expected_sources, k)
        metrics[f"recall@{k}"] = recall_at_k(sources, expected_sources, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(sources, expected_sources, k)

    return metrics


def aggregate_retrieval_metrics(
    per_query_metrics: List[Dict[str, float]],
) -> Dict[str, float]:
    """Average retrieval metrics across multiple queries.

    Args:
        per_query_metrics: List of metric dicts from compute_retrieval_metrics.

    Returns:
        Dict of metric_name → average value.
    """
    if not per_query_metrics:
        return {}

    all_keys = per_query_metrics[0].keys()
    aggregated = {}

    for key in all_keys:
        values = [m[key] for m in per_query_metrics if key in m]
        aggregated[f"avg_{key}"] = sum(values) / len(values) if values else 0.0

    return aggregated
