#!/usr/bin/env python3
"""
View evaluation history ledger.

Usage:
    python evaluation/view_history.py              # Show all runs
    python evaluation/view_history.py --last 5     # Last 5 runs
    python evaluation/view_history.py --dataset fx5u  # Filter by dataset
"""

import argparse
import json
from pathlib import Path

HISTORY_PATH = Path(__file__).parent / "results" / "history.jsonl"


def load_history() -> list[dict]:
    """Load all entries from the history ledger."""
    if not HISTORY_PATH.exists():
        return []
    entries = []
    for line in HISTORY_PATH.read_text().strip().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def clean_history():
    """Remove entries with empty dataset or 0 queries."""
    entries = load_history()
    before = len(entries)
    kept = [e for e in entries if e.get("dataset", "").strip() and e.get("query_count", 0) > 0]
    removed = before - len(kept)

    if removed == 0:
        print("No noise entries found.")
        return

    with open(HISTORY_PATH, "w") as f:
        for e in kept:
            f.write(json.dumps(e, default=str) + "\n")

    print(f"Removed {removed} noise entries ({before} → {len(kept)})")


def print_table(entries: list[dict]):
    """Print entries as a formatted table."""
    if not entries:
        print("No history entries found.")
        return

    # Header
    header = f"{'Run ID':<28} {'Dataset':<22} {'Qs':>3}  {'Overall':>7}  {'Acc':>5}  {'Comp':>5}  {'Sim':>6}  {'P50ms':>7}  {'Label'}"
    sep = "\u2500" * len(header)
    print(header)
    print(sep)

    for e in entries:
        m = e.get("metrics", {})
        overall = m.get("overall")
        accuracy = m.get("accuracy")
        completeness = m.get("completeness")
        sim = m.get("semantic_similarity")
        p50 = m.get("latency_p50_ms")

        overall_s = f"{overall:.2f}" if overall is not None else "  -  "
        acc_s = f"{accuracy:.2f}" if accuracy is not None else "  -  "
        comp_s = f"{completeness:.2f}" if completeness is not None else "  -  "
        sim_s = f"{sim:.3f}" if sim is not None else "  -  "
        p50_s = f"{p50:.0f}" if p50 is not None else "  -  "

        dataset_short = (e.get("dataset", "")[:20] or "-")
        run_id = (e.get("run_id", "")[:26] or "-")
        label = e.get("label", "")

        print(
            f"{run_id:<28} {dataset_short:<22} {e.get('query_count', 0):>3}  "
            f"{overall_s:>7}  {acc_s:>5}  {comp_s:>5}  {sim_s:>6}  {p50_s:>7}  {label}"
        )

    print(f"\n{len(entries)} run(s)")


def print_detail(entries: list[dict]):
    """Print entries with full config details."""
    if not entries:
        print("No history entries found.")
        return

    # Key config fields to highlight (skip obvious/static ones)
    config_keys = [
        "embedding_model", "chunk_size", "chunk_overlap", "top_k",
        "use_hybrid", "hybrid_alpha", "use_reranking", "use_query_expansion",
        "use_adaptive_alpha", "reranker_blending",
    ]

    for i, e in enumerate(entries):
        m = e.get("metrics", {})
        config = e.get("config", {})

        print(f"{'═' * 80}")
        print(f"  Run:     {e.get('run_id', '-')}")
        print(f"  Date:    {e.get('timestamp', '-')}")
        print(f"  Dataset: {e.get('dataset', '-')}  ({e.get('query_count', 0)} questions)")
        print(f"  Label:   {e.get('label', '-')}")
        print()

        # Metrics
        overall = m.get("overall")
        print(f"  Metrics:")
        print(f"    Overall={_fmt(overall)}  Acc={_fmt(m.get('accuracy'))}  "
              f"Comp={_fmt(m.get('completeness'))}  Org={_fmt(m.get('organization'))}  "
              f"Rel={_fmt(m.get('relevance'))}")
        print(f"    Sim={_fmt(m.get('semantic_similarity'), 3)}  "
              f"ROUGE-L={_fmt(m.get('rouge_l'), 3)}  "
              f"NDCG@5={_fmt(m.get('avg_ndcg5'), 3)}  "
              f"P50={_fmt(m.get('latency_p50_ms'), 0)}ms  "
              f"P95={_fmt(m.get('latency_p95_ms'), 0)}ms")
        print()

        # Config
        if config:
            print(f"  Config:")
            for key in config_keys:
                if key in config:
                    print(f"    {key}: {config[key]}")
        print()

    print(f"{len(entries)} run(s)")


def _fmt(val, decimals=2):
    """Format a metric value."""
    if val is None:
        return "-"
    if decimals == 0:
        return f"{val:.0f}"
    return f"{val:.{decimals}f}"


def main():
    parser = argparse.ArgumentParser(description="View evaluation history")
    parser.add_argument("--dataset", help="Filter by dataset name (substring match)")
    parser.add_argument("--last", type=int, help="Show only last N runs")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--detail", action="store_true", help="Show full config for each run")
    parser.add_argument("--clean", action="store_true", help="Remove entries with empty dataset or 0 queries")
    args = parser.parse_args()

    if args.clean:
        clean_history()
        return

    entries = load_history()

    if args.dataset:
        entries = [e for e in entries if args.dataset.lower() in e.get("dataset", "").lower()]

    if args.last:
        entries = entries[-args.last:]

    if args.json:
        for e in entries:
            print(json.dumps(e))
    elif args.detail:
        print_detail(entries)
    else:
        print_table(entries)


if __name__ == "__main__":
    main()
