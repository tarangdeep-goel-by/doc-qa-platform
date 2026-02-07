"""Shared helpers for eval history ledger construction."""


def build_metrics_entry(summary: dict) -> dict:
    """Extract standardized metrics dict from an eval results summary.

    Used by both run_evaluation.append_to_history() and backfill_history.build_entry().
    """
    aq = summary.get("answer_quality", {})
    perf = summary.get("performance", {})
    latency = perf.get("latency_ms", {})

    return {
        "overall": aq.get("avg_judge_overall"),
        "accuracy": aq.get("avg_judge_accuracy"),
        "completeness": aq.get("avg_judge_completeness"),
        "organization": aq.get("avg_judge_organization"),
        "relevance": aq.get("avg_judge_relevance"),
        "semantic_similarity": round(aq.get("avg_semantic_similarity", 0), 4),
        "rouge_l": round(aq.get("avg_rouge_l", 0), 4),
        "avg_ndcg5": round(summary.get("retrieval", {}).get("avg_ndcg@5", 0), 4),
        "latency_p50_ms": round(latency.get("p50", 0), 1),
        "latency_p95_ms": round(latency.get("p95", 0), 1),
        "latency_mean_ms": round(latency.get("mean", 0), 1),
        "latency_max_ms": round(latency.get("max", 0), 1),
    }
