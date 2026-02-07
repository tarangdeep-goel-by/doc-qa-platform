"""Performance metrics: latency tracking and throughput measurement."""

import math
import time
import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class LatencyRecord:
    """A single latency measurement."""
    question_id: str
    total_ms: float
    embedding_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0


class PerformanceTracker:
    """Track and aggregate performance metrics across queries."""

    def __init__(self):
        self.records: List[LatencyRecord] = []
        self._start_time: Optional[float] = None

    def start_suite(self):
        """Mark the start of an evaluation suite."""
        self._start_time = time.time()

    def record(self, record: LatencyRecord):
        """Add a latency record."""
        self.records.append(record)

    def compute_stats(self) -> Dict[str, Any]:
        """Compute aggregate performance statistics.

        Returns:
            Dict with p50/p95/p99 latency, throughput, and per-stage breakdown.
        """
        if not self.records:
            return {"error": "No records"}

        totals = sorted(r.total_ms for r in self.records)
        n = len(totals)

        stats: Dict[str, Any] = {
            "query_count": n,
            "latency_ms": {
                "min": round(totals[0], 1),
                "max": round(totals[-1], 1),
                "mean": round(statistics.mean(totals), 1),
                "p50": round(totals[n // 2], 1),
                "p95": round(totals[int(n * 0.95)], 1) if n >= 20 else round(totals[-1], 1),
                "p99": round(totals[min(int(math.ceil(n * 0.99)) - 1, n - 1)], 1) if n >= 100 else round(totals[-1], 1),
            },
        }

        # Per-stage breakdown (if recorded)
        for stage in ["embedding", "retrieval", "reranking", "generation"]:
            values = [getattr(r, f"{stage}_ms") for r in self.records if getattr(r, f"{stage}_ms") > 0]
            if values:
                stats[f"{stage}_ms"] = {
                    "mean": round(statistics.mean(values), 1),
                    "p50": round(sorted(values)[len(values) // 2], 1),
                }

        # Throughput
        if self._start_time:
            elapsed_s = time.time() - self._start_time
            stats["throughput"] = {
                "total_seconds": round(elapsed_s, 1),
                "queries_per_second": round(n / elapsed_s, 2) if elapsed_s > 0 else 0,
            }

        return stats

    def to_records_list(self) -> List[Dict[str, Any]]:
        """Export all records as list of dicts."""
        return [asdict(r) for r in self.records]


class Timer:
    """Context manager for timing code blocks.

    Usage:
        with Timer() as t:
            do_something()
        print(t.elapsed_ms)
    """

    def __init__(self):
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.time() - self._start) * 1000
