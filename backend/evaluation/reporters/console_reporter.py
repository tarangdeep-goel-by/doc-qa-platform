"""Pretty-print evaluation results to terminal."""

from typing import Dict, Any, List


def print_header(title: str, width: int = 80):
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def print_section(title: str, width: int = 80):
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def report_query_result(result: Dict[str, Any], index: int):
    """Print results for a single query."""
    q = result.get("question", "?")
    print(f"\n  Q{index}: {q}")

    # Answer comparison
    our = result.get("our_answer", "")
    ref = result.get("claude_answer", "")
    print(f"  Our answer:    {our[:120]}{'...' if len(our) > 120 else ''}")
    print(f"  Reference:     {ref[:120]}{'...' if len(ref) > 120 else ''}")

    # Retrieval metrics
    retrieval = result.get("retrieval_metrics", {})
    if retrieval:
        parts = []
        for key in ["ndcg@5", "mrr", "precision@5", "recall@5"]:
            if key in retrieval:
                parts.append(f"{key}={retrieval[key]:.3f}")
        print(f"  Retrieval:     {', '.join(parts)}")

    # Answer quality metrics
    answer = result.get("answer_metrics", {})
    if answer:
        parts = []
        for key in ["rouge_l", "rouge_1", "semantic_similarity"]:
            if key in answer:
                parts.append(f"{key}={answer[key]:.3f}")
        print(f"  Answer:        {', '.join(parts)}")

        judge = answer.get("llm_judge", {})
        if judge and not judge.get("error"):
            parts = [f"{k}={v}" for k, v in judge.items()
                     if k not in ("explanation", "error") and isinstance(v, (int, float))]
            print(f"  LLM Judge:     {', '.join(parts)}")

    # Sources
    sources = result.get("sources", [])
    if sources:
        top3 = sources[:3]
        src_str = ", ".join(
            f"p.{s.get('page_num', '?')} ({s.get('score', 0):.0%})"
            for s in top3
        )
        print(f"  Top sources:   {src_str}")

    # Latency
    latency = result.get("latency_ms")
    if latency:
        print(f"  Latency:       {latency:.0f}ms")


def report_summary(results: Dict[str, Any]):
    """Print the aggregated summary."""
    print_header("EVALUATION SUMMARY")

    summary = results.get("summary", {})

    # Retrieval summary
    retrieval = summary.get("retrieval", {})
    if retrieval:
        print_section("Retrieval Quality")
        for key, val in sorted(retrieval.items()):
            bar = _bar(val, max_val=1.0) if isinstance(val, float) else ""
            print(f"    {key:25s}  {val:.4f}  {bar}")

    # Answer quality summary
    answer = summary.get("answer_quality", {})
    if answer:
        print_section("Answer Quality")
        for key, val in sorted(answer.items()):
            if isinstance(val, float):
                max_v = 5.0 if "judge" in key else 1.0
                bar = _bar(val, max_val=max_v)
                fmt = f"{val:.2f}" if max_v > 1 else f"{val:.4f}"
                print(f"    {key:25s}  {fmt:>8s}  {bar}")

    # Performance summary
    perf = summary.get("performance", {})
    if perf:
        print_section("Performance")
        latency = perf.get("latency_ms", {})
        for key in ["mean", "p50", "p95"]:
            if key in latency:
                print(f"    latency_{key:10s}  {latency[key]:>8.0f}ms")
        throughput = perf.get("throughput", {})
        if "queries_per_second" in throughput:
            print(f"    {'throughput':15s}  {throughput['queries_per_second']:.2f} q/s")

    # Config
    config = results.get("config", {})
    if config:
        print_section("Configuration")
        for key, val in sorted(config.items()):
            print(f"    {key:25s}  {val}")

    print(f"\n{'=' * 80}\n")


def report_comparison(baseline: Dict[str, Any], experiment: Dict[str, Any]):
    """Print side-by-side comparison of two evaluation runs."""
    print_header("EXPERIMENT COMPARISON")

    b_summary = baseline.get("summary", {})
    e_summary = experiment.get("summary", {})

    # Compare retrieval
    b_ret = b_summary.get("retrieval", {})
    e_ret = e_summary.get("retrieval", {})
    if b_ret or e_ret:
        print_section("Retrieval Quality")
        print(f"    {'Metric':25s}  {'Baseline':>10s}  {'Experiment':>10s}  {'Delta':>10s}")
        all_keys = sorted(set(list(b_ret.keys()) + list(e_ret.keys())))
        for key in all_keys:
            b_val = b_ret.get(key, 0.0)
            e_val = e_ret.get(key, 0.0)
            delta = e_val - b_val
            arrow = "+" if delta > 0 else ""
            color = "^" if delta > 0.01 else ("v" if delta < -0.01 else "=")
            print(f"    {key:25s}  {b_val:10.4f}  {e_val:10.4f}  {arrow}{delta:+.4f} {color}")

    # Compare answer quality
    b_ans = b_summary.get("answer_quality", {})
    e_ans = e_summary.get("answer_quality", {})
    if b_ans or e_ans:
        print_section("Answer Quality")
        print(f"    {'Metric':25s}  {'Baseline':>10s}  {'Experiment':>10s}  {'Delta':>10s}")
        all_keys = sorted(set(list(b_ans.keys()) + list(e_ans.keys())))
        for key in all_keys:
            b_val = b_ans.get(key, 0.0)
            e_val = e_ans.get(key, 0.0)
            delta = e_val - b_val
            arrow = "+" if delta > 0 else ""
            print(f"    {key:25s}  {b_val:10.4f}  {e_val:10.4f}  {arrow}{delta:+.4f}")

    print(f"\n{'=' * 80}\n")


def _bar(value: float, max_val: float = 1.0, width: int = 20) -> str:
    """Render a simple ASCII progress bar."""
    ratio = min(value / max_val, 1.0) if max_val > 0 else 0
    filled = int(ratio * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"
