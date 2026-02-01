"""Generate HTML comparison reports for evaluation results."""

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


def generate_report(
    results: Dict[str, Any],
    output_path: str,
    title: str = "RAG Evaluation Report",
):
    """Generate a standalone HTML report from evaluation results.

    Args:
        results: Full evaluation results dict.
        output_path: Path to write HTML file.
        title: Report title.
    """
    html = _build_html(results, title)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML report saved to: {output_path}")


def generate_comparison_report(
    baseline: Dict[str, Any],
    experiment: Dict[str, Any],
    output_path: str,
    title: str = "RAG Experiment Comparison",
):
    """Generate HTML comparing two evaluation runs.

    Args:
        baseline: Baseline evaluation results.
        experiment: Experiment evaluation results.
        output_path: Path to write HTML file.
        title: Report title.
    """
    html = _build_comparison_html(baseline, experiment, title)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Comparison report saved to: {output_path}")


def _build_html(results: Dict[str, Any], title: str) -> str:
    summary = results.get("summary", {})
    queries = results.get("queries", [])
    config = results.get("config", {})
    timestamp = results.get("timestamp", datetime.now().isoformat())

    # Build query rows
    query_rows = ""
    for i, q in enumerate(queries, 1):
        r_metrics = q.get("retrieval_metrics", {})
        a_metrics = q.get("answer_metrics", {})
        judge = a_metrics.get("llm_judge", {})

        query_rows += f"""
        <tr>
            <td>{i}</td>
            <td class="question">{_esc(q.get('question', ''))}</td>
            <td>{r_metrics.get('ndcg@5', 0):.3f}</td>
            <td>{r_metrics.get('mrr', 0):.3f}</td>
            <td>{a_metrics.get('rouge_l', 0):.3f}</td>
            <td>{a_metrics.get('semantic_similarity', 0):.3f}</td>
            <td>{judge.get('overall', 0):.1f}</td>
            <td>{q.get('latency_ms', 0):.0f}ms</td>
        </tr>"""

    # Summary metrics
    ret = summary.get("retrieval", {})
    ans = summary.get("answer_quality", {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_esc(title)}</title>
<style>{_css()}</style>
</head>
<body>
<div class="container">
    <h1>{_esc(title)}</h1>
    <p class="timestamp">Generated: {timestamp}</p>

    <h2>Summary</h2>
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Avg NDCG@5</div>
            <div class="metric-value">{ret.get('avg_ndcg@5', 0):.3f}</div>
            {_bar_html(ret.get('avg_ndcg@5', 0))}
        </div>
        <div class="metric-card">
            <div class="metric-label">Avg MRR</div>
            <div class="metric-value">{ret.get('avg_mrr', 0):.3f}</div>
            {_bar_html(ret.get('avg_mrr', 0))}
        </div>
        <div class="metric-card">
            <div class="metric-label">Avg Semantic Similarity</div>
            <div class="metric-value">{ans.get('avg_semantic_similarity', 0):.3f}</div>
            {_bar_html(ans.get('avg_semantic_similarity', 0))}
        </div>
        <div class="metric-card">
            <div class="metric-label">Avg ROUGE-L</div>
            <div class="metric-value">{ans.get('avg_rouge_l', 0):.3f}</div>
            {_bar_html(ans.get('avg_rouge_l', 0))}
        </div>
        <div class="metric-card">
            <div class="metric-label">Avg LLM Judge</div>
            <div class="metric-value">{ans.get('avg_judge_overall', 0):.1f}/5</div>
            {_bar_html(ans.get('avg_judge_overall', 0), 5.0)}
        </div>
    </div>

    <h2>Per-Query Results</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Question</th>
                <th>NDCG@5</th>
                <th>MRR</th>
                <th>ROUGE-L</th>
                <th>Similarity</th>
                <th>Judge</th>
                <th>Latency</th>
            </tr>
        </thead>
        <tbody>
            {query_rows}
        </tbody>
    </table>

    <h2>Configuration</h2>
    <pre>{json.dumps(config, indent=2)}</pre>

    <h2>Raw Results</h2>
    <details>
        <summary>Click to expand full JSON</summary>
        <pre>{json.dumps(results, indent=2, default=str)}</pre>
    </details>
</div>
</body>
</html>"""


def _build_comparison_html(
    baseline: Dict[str, Any],
    experiment: Dict[str, Any],
    title: str,
) -> str:
    b_sum = baseline.get("summary", {})
    e_sum = experiment.get("summary", {})

    # Build comparison rows for retrieval
    b_ret = b_sum.get("retrieval", {})
    e_ret = e_sum.get("retrieval", {})
    ret_rows = _comparison_rows(b_ret, e_ret)

    # Build comparison rows for answer quality
    b_ans = b_sum.get("answer_quality", {})
    e_ans = e_sum.get("answer_quality", {})
    ans_rows = _comparison_rows(b_ans, e_ans)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_esc(title)}</title>
<style>{_css()}</style>
</head>
<body>
<div class="container">
    <h1>{_esc(title)}</h1>
    <p class="timestamp">Generated: {datetime.now().isoformat()}</p>

    <h2>Retrieval Quality</h2>
    <table>
        <thead>
            <tr><th>Metric</th><th>Baseline</th><th>Experiment</th><th>Delta</th></tr>
        </thead>
        <tbody>{ret_rows}</tbody>
    </table>

    <h2>Answer Quality</h2>
    <table>
        <thead>
            <tr><th>Metric</th><th>Baseline</th><th>Experiment</th><th>Delta</th></tr>
        </thead>
        <tbody>{ans_rows}</tbody>
    </table>

    <h2>Raw Data</h2>
    <details>
        <summary>Baseline JSON</summary>
        <pre>{json.dumps(baseline, indent=2, default=str)}</pre>
    </details>
    <details>
        <summary>Experiment JSON</summary>
        <pre>{json.dumps(experiment, indent=2, default=str)}</pre>
    </details>
</div>
</body>
</html>"""


def _comparison_rows(baseline: Dict, experiment: Dict) -> str:
    rows = ""
    all_keys = sorted(set(list(baseline.keys()) + list(experiment.keys())))
    for key in all_keys:
        b = baseline.get(key, 0.0)
        e = experiment.get(key, 0.0)
        delta = e - b
        css = "positive" if delta > 0.005 else ("negative" if delta < -0.005 else "neutral")
        sign = "+" if delta > 0 else ""
        rows += f"""
        <tr>
            <td>{_esc(key)}</td>
            <td>{b:.4f}</td>
            <td>{e:.4f}</td>
            <td class="{css}">{sign}{delta:.4f}</td>
        </tr>"""
    return rows


def _bar_html(value: float, max_val: float = 1.0) -> str:
    pct = min(value / max_val * 100, 100) if max_val > 0 else 0
    color = "#22c55e" if pct >= 80 else ("#eab308" if pct >= 50 else "#ef4444")
    return f'<div class="bar"><div class="bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _css() -> str:
    return """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f172a; color: #e2e8f0; padding: 2rem; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; color: #f8fafc; }
    h2 { font-size: 1.3rem; margin: 2rem 0 1rem; color: #94a3b8; }
    .timestamp { color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }
    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem; margin-bottom: 2rem; }
    .metric-card { background: #1e293b; border-radius: 8px; padding: 1.2rem;
                   border: 1px solid #334155; }
    .metric-label { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.3rem; }
    .metric-value { font-size: 1.6rem; font-weight: 700; color: #f8fafc; }
    .bar { height: 6px; background: #334155; border-radius: 3px; margin-top: 0.5rem; }
    .bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
    th { background: #1e293b; padding: 0.7rem; text-align: left; font-size: 0.8rem;
         color: #94a3b8; border-bottom: 2px solid #334155; }
    td { padding: 0.6rem 0.7rem; border-bottom: 1px solid #1e293b; font-size: 0.85rem; }
    tr:hover td { background: #1e293b; }
    .question { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .positive { color: #22c55e; font-weight: 600; }
    .negative { color: #ef4444; font-weight: 600; }
    .neutral { color: #94a3b8; }
    pre { background: #1e293b; padding: 1rem; border-radius: 8px; overflow-x: auto;
          font-size: 0.8rem; line-height: 1.5; border: 1px solid #334155; }
    details { margin-bottom: 1rem; }
    summary { cursor: pointer; color: #60a5fa; font-size: 0.9rem; padding: 0.5rem 0; }
    """
