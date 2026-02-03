#!/usr/bin/env python3
"""
Main evaluation entry point - run full eval suite against benchmark dataset.

Usage:
    python evaluation/run_evaluation.py \
        --dataset evaluation/datasets/fx5u_qa_benchmark.json \
        --output evaluation/results/baseline.json

    # Skip LLM judge (faster, no API cost):
    python evaluation/run_evaluation.py \
        --dataset evaluation/datasets/fx5u_qa_benchmark.json \
        --output evaluation/results/baseline.json \
        --no-judge

    # Compare two runs:
    python evaluation/run_evaluation.py \
        --compare evaluation/results/baseline.json evaluation/results/experiment.json \
        --output evaluation/results/comparison.html
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from evaluation.benchmark_dataset import BenchmarkDataset
from evaluation.metrics.retrieval import (
    compute_retrieval_metrics,
    aggregate_retrieval_metrics,
)
from evaluation.metrics.answer_quality import (
    compute_answer_metrics,
    aggregate_answer_metrics,
)
from evaluation.metrics.performance import PerformanceTracker, Timer, LatencyRecord
from evaluation.reporters import console_reporter, html_reporter


def init_components():
    """Initialize RAG pipeline components from .env config."""
    from src.embedder import Embedder
    from src.vector_store import VectorStore
    from src.qa_engine import QAEngine

    embedding_model = os.environ["EMBEDDING_MODEL"]
    qdrant_host = os.environ["QDRANT_HOST"]
    qdrant_port = int(os.environ["QDRANT_PORT"])
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    model_name = os.environ["GEMINI_MODEL"]
    embedding_dim = int(os.environ["EMBEDDING_DIM"])

    print("Initializing components...")
    embedder = Embedder(
        model_name=embedding_model,
        gemini_api_key=gemini_api_key,
        output_dimensionality=embedding_dim,
    )
    vector_store = VectorStore(
        host=qdrant_host, port=qdrant_port,
        collection_name="documents",
        vector_size=embedding_dim,
        bm25_cache_dir=os.environ["BM25_CACHE_DIR"],
    )
    qa_engine = QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        model_name=model_name,
        use_reranker=os.environ["USE_RERANKING"].lower() == "true",
        reranker_model=os.environ["RERANKER_MODEL"],
    )
    print("Components ready.")

    return embedder, vector_store, qa_engine, gemini_api_key, model_name


def get_rag_config() -> dict:
    """Read current RAG config from environment."""
    return {
        "embedding_model": os.environ["EMBEDDING_MODEL"],
        "embedding_dim": os.environ["EMBEDDING_DIM"],
        "chunk_size": os.environ["CHUNK_SIZE"],
        "chunk_overlap": os.environ["CHUNK_OVERLAP"],
        "top_k": os.environ["TOP_K_RESULTS"],
        "use_hybrid": os.environ["USE_HYBRID_SEARCH"],
        "hybrid_alpha": os.environ["HYBRID_ALPHA"],
        "use_reranking": os.environ["USE_RERANKING"],
        "use_query_expansion": os.environ["USE_QUERY_EXPANSION"],
        "query_expansion_variants": os.environ["QUERY_EXPANSION_VARIANTS"],
        "use_rrf": os.environ["USE_RRF"],
        "reranker_blending": os.environ["RERANKER_BLENDING"],
        "use_query_decomposition": os.environ["USE_QUERY_DECOMPOSITION"],
    }


def run_evaluation(
    dataset: BenchmarkDataset,
    qa_engine,
    embedder,
    gemini_api_key: str,
    model_name: str,
    doc_ids: list = None,
    use_judge: bool = True,
    feature_ablation: bool = False,
) -> dict:
    """Run full evaluation suite on a benchmark dataset.

    Args:
        dataset: Loaded benchmark dataset.
        qa_engine: Initialized QAEngine.
        embedder: Initialized Embedder (for semantic similarity).
        gemini_api_key: For LLM-as-judge.
        model_name: Gemini model name.
        doc_ids: Optional list of doc IDs to constrain search.
        use_judge: Whether to run LLM-as-judge (slower, costs API).
        feature_ablation: If True, run with/without features for A/B comparison.

    Returns:
        Full results dict with per-query and aggregate metrics.
    """
    from google import genai

    client = genai.Client(api_key=gemini_api_key) if use_judge else None
    config = get_rag_config()
    perf = PerformanceTracker()
    perf.start_suite()

    # Read RAG params from env
    top_k = int(os.environ["TOP_K_RESULTS"])
    use_hybrid = os.environ["USE_HYBRID_SEARCH"].lower() == "true"
    hybrid_alpha = float(os.environ["HYBRID_ALPHA"])
    use_reranking = os.environ["USE_RERANKING"].lower() == "true"
    use_query_expansion = os.environ["USE_QUERY_EXPANSION"].lower() == "true"
    query_expansion_variants = int(os.environ["QUERY_EXPANSION_VARIANTS"])
    use_rrf = os.environ["USE_RRF"].lower() == "true"
    rerank_blending = os.environ["RERANKER_BLENDING"]

    per_query_results = []
    all_retrieval_metrics = []
    all_answer_metrics = []

    print(f"\nRunning {len(dataset.questions)} benchmark queries...")
    print(f"  LLM judge: {'ON' if use_judge else 'OFF'}")
    print(f"  Doc filter: {doc_ids if doc_ids else 'all docs'}")

    for i, bq in enumerate(dataset.questions, 1):
        print(f"\n[{i}/{len(dataset.questions)}] {bq.question}")

        # Time the full query
        with Timer() as total_timer:
            result = qa_engine.answer_question(
                question=bq.question,
                top_k=top_k,
                doc_ids=doc_ids,
                use_hybrid=use_hybrid,
                hybrid_alpha=hybrid_alpha,
                use_reranking=use_reranking,
                use_query_expansion=use_query_expansion,
                query_expansion_variants=query_expansion_variants,
                use_rrf=use_rrf,
                rerank_blending=rerank_blending,
            )

        our_answer = result.get("answer", "")
        sources = result.get("sources", [])

        # Retrieval metrics
        retrieval_metrics = compute_retrieval_metrics(
            sources=sources,
            expected_sources=bq.expected_sources,
        )
        all_retrieval_metrics.append(retrieval_metrics)

        # Answer quality metrics
        answer_metrics = compute_answer_metrics(
            our_answer=our_answer,
            reference_answer=bq.claude_answer,
            embedder=embedder,
            client=client if use_judge else None,
            question=bq.question,
            model_name=model_name,
        )
        all_answer_metrics.append(answer_metrics)

        # Performance record
        perf.record(LatencyRecord(
            question_id=bq.id,
            total_ms=total_timer.elapsed_ms,
        ))

        # Build per-query result
        query_result = {
            "question_id": bq.id,
            "question": bq.question,
            "difficulty": bq.difficulty,
            "category": bq.category,
            "our_answer": our_answer,
            "claude_answer": bq.claude_answer,
            "sources": sources,
            "retrieval_metrics": retrieval_metrics,
            "answer_metrics": answer_metrics,
            "latency_ms": round(total_timer.elapsed_ms, 1),
            "low_confidence": result.get("low_confidence", False),
        }
        per_query_results.append(query_result)

        # Print quick summary
        ndcg = retrieval_metrics.get("ndcg@5", 0)
        sim = answer_metrics.get("semantic_similarity", 0)
        rl = answer_metrics.get("rouge_l", 0)
        print(f"  NDCG@5={ndcg:.3f}  Sim={sim:.3f}  ROUGE-L={rl:.3f}  {total_timer.elapsed_ms:.0f}ms")

    # Aggregate metrics
    agg_retrieval = aggregate_retrieval_metrics(all_retrieval_metrics)
    agg_answer = aggregate_answer_metrics(all_answer_metrics)
    perf_stats = perf.compute_stats()

    # Feature ablation (optional)
    ablation_results = {}
    if feature_ablation:
        ablation_results = _run_ablation(
            dataset, qa_engine, embedder, doc_ids, top_k
        )

    results = {
        "timestamp": datetime.now().isoformat(),
        "dataset": dataset.dataset_name,
        "document": dataset.document,
        "query_count": len(dataset.questions),
        "config": config,
        "queries": per_query_results,
        "summary": {
            "retrieval": agg_retrieval,
            "answer_quality": agg_answer,
            "performance": perf_stats,
        },
    }

    if ablation_results:
        results["ablation"] = ablation_results

    return results


def _run_ablation(dataset, qa_engine, embedder, doc_ids, top_k) -> dict:
    """Run A/B tests with features toggled on/off.

    Tests: query expansion, reranking, RRF.
    """
    print("\n\nRunning feature ablation...")
    ablation = {}

    configs = [
        ("no_query_expansion", {"use_query_expansion": False}),
        ("no_reranking", {"use_reranking": False}),
        ("no_rrf", {"use_rrf": False}),
        ("vector_only", {"use_hybrid": False, "use_query_expansion": False}),
    ]

    for name, overrides in configs:
        print(f"\n  Ablation: {name}")
        metrics_list = []

        for bq in dataset.questions:
            params = {
                "question": bq.question,
                "top_k": top_k,
                "doc_ids": doc_ids,
                "use_hybrid": True,
                "use_reranking": True,
                "use_query_expansion": True,
                "use_rrf": True,
            }
            params.update(overrides)

            result = qa_engine.answer_question(**params)
            sources = result.get("sources", [])

            metrics = compute_retrieval_metrics(sources, bq.expected_sources)
            metrics_list.append(metrics)

        ablation[name] = aggregate_retrieval_metrics(metrics_list)
        ndcg = ablation[name].get("avg_ndcg@5", 0)
        print(f"    avg_ndcg@5 = {ndcg:.4f}")

    return ablation


def compare_experiments(baseline_path: str, experiment_path: str, output_path: str):
    """Load two result files and generate comparison report."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(experiment_path) as f:
        experiment = json.load(f)

    # Console comparison
    console_reporter.report_comparison(baseline, experiment)

    # HTML comparison
    if output_path.endswith(".html"):
        html_reporter.generate_comparison_report(baseline, experiment, output_path)
    else:
        # JSON diff
        b_sum = baseline.get("summary", {})
        e_sum = experiment.get("summary", {})
        diff = {
            "baseline_file": baseline_path,
            "experiment_file": experiment_path,
            "retrieval_delta": {},
            "answer_delta": {},
        }

        for key in set(
            list(b_sum.get("retrieval", {}).keys())
            + list(e_sum.get("retrieval", {}).keys())
        ):
            b_val = b_sum.get("retrieval", {}).get(key, 0)
            e_val = e_sum.get("retrieval", {}).get(key, 0)
            diff["retrieval_delta"][key] = round(e_val - b_val, 4)

        for key in set(
            list(b_sum.get("answer_quality", {}).keys())
            + list(e_sum.get("answer_quality", {}).keys())
        ):
            b_val = b_sum.get("answer_quality", {}).get(key, 0)
            e_val = e_sum.get("answer_quality", {}).get(key, 0)
            diff["answer_delta"][key] = round(e_val - b_val, 4)

        with open(output_path, "w") as f:
            json.dump(diff, f, indent=2)
        print(f"Comparison saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Suite")
    parser.add_argument(
        "--dataset",
        help="Path to benchmark dataset JSON",
    )
    parser.add_argument(
        "--output",
        default="evaluation/results/eval_result.json",
        help="Output path for results (JSON or HTML)",
    )
    parser.add_argument(
        "--doc-ids",
        nargs="*",
        help="Document IDs to constrain search",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip LLM-as-judge (faster, no API cost)",
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Run feature ablation tests",
    )
    parser.add_argument(
        "--html",
        help="Also generate HTML report at this path",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE", "EXPERIMENT"),
        help="Compare two result files instead of running eval",
    )

    args = parser.parse_args()

    # Comparison mode
    if args.compare:
        compare_experiments(args.compare[0], args.compare[1], args.output)
        return

    # Evaluation mode
    if not args.dataset:
        parser.error("--dataset is required for evaluation mode")

    dataset = BenchmarkDataset.from_file(args.dataset)
    print(f"Loaded dataset: {dataset.dataset_name}")
    print(f"  Document: {dataset.document}")
    print(f"  Questions: {len(dataset.questions)}")

    embedder, vector_store, qa_engine, gemini_api_key, model_name = init_components()

    results = run_evaluation(
        dataset=dataset,
        qa_engine=qa_engine,
        embedder=embedder,
        gemini_api_key=gemini_api_key,
        model_name=model_name,
        doc_ids=args.doc_ids,
        use_judge=not args.no_judge,
        feature_ablation=args.ablation,
    )

    # Save JSON results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    # Console report
    console_reporter.report_summary(results)
    for i, q in enumerate(results["queries"], 1):
        console_reporter.report_query_result(q, i)

    # HTML report
    if args.html:
        html_reporter.generate_report(results, args.html)


if __name__ == "__main__":
    main()
