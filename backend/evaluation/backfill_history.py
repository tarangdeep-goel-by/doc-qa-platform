#!/usr/bin/env python3
"""
One-time backfill: read all existing eval result JSONs and append to history.jsonl.

Usage:
    python evaluation/backfill_history.py
    python evaluation/backfill_history.py --dry-run   # Preview without writing
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
HISTORY_PATH = RESULTS_DIR / "history.jsonl"


def build_entry(result_file: Path) -> dict | None:
    """Build a history entry from a result JSON file."""
    try:
        data = json.loads(result_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"  SKIP {result_file.name}: {e}")
        return None

    # Must have summary to be a valid eval result
    summary = data.get("summary")
    if not summary:
        print(f"  SKIP {result_file.name}: no summary")
        return None

    aq = summary.get("answer_quality", {})
    perf = summary.get("performance", {})

    timestamp = data.get("timestamp", "")
    # Build run_id from timestamp + filename stem
    try:
        ts = datetime.fromisoformat(timestamp)
        run_id = f"{ts.strftime('%Y%m%d_%H%M')}_{result_file.stem[:20]}"
    except (ValueError, TypeError):
        run_id = f"unknown_{result_file.stem[:20]}"

    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "dataset": data.get("dataset", ""),
        "document": data.get("document", ""),
        "query_count": data.get("query_count", 0),
        "config": data.get("config", {}),
        "metrics": {
            "overall": aq.get("avg_judge_overall"),
            "accuracy": aq.get("avg_judge_accuracy"),
            "completeness": aq.get("avg_judge_completeness"),
            "organization": aq.get("avg_judge_organization"),
            "relevance": aq.get("avg_judge_relevance"),
            "semantic_similarity": round(aq.get("avg_semantic_similarity", 0), 4),
            "rouge_l": round(aq.get("avg_rouge_l", 0), 4),
            "avg_ndcg5": round(summary.get("retrieval", {}).get("avg_ndcg@5", 0), 4),
            "latency_p50_ms": round(perf.get("latency_ms", {}).get("p50", 0), 1),
        },
        "label": "(backfill)",
        "result_file": result_file.name,
    }


def main():
    parser = argparse.ArgumentParser(description="Backfill eval history from existing results")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    result_files = sorted(RESULTS_DIR.glob("*.json"))
    print(f"Found {len(result_files)} JSON files in {RESULTS_DIR}")

    # Check existing history to avoid duplicates
    existing_files = set()
    if HISTORY_PATH.exists():
        for line in HISTORY_PATH.read_text().strip().splitlines():
            if line.strip():
                entry = json.loads(line)
                existing_files.add(entry.get("result_file", ""))

    entries = []
    for f in result_files:
        if f.name in existing_files:
            print(f"  SKIP {f.name}: already in history")
            continue
        entry = build_entry(f)
        if entry:
            entries.append(entry)

    # Sort by timestamp
    entries.sort(key=lambda e: e.get("timestamp", ""))

    print(f"\n{len(entries)} new entries to add")

    if args.dry_run:
        for e in entries:
            print(f"  {e['run_id']}  {e['dataset'][:30]}  Qs={e['query_count']}  overall={e['metrics'].get('overall')}")
        print("\nDry run — nothing written.")
        return

    with open(HISTORY_PATH, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")

    print(f"Appended {len(entries)} entries to {HISTORY_PATH}")


if __name__ == "__main__":
    main()
