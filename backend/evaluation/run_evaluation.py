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
from datetime import datetime
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from evaluation.benchmark_dataset import (
    BenchmarkDataset,
    ConversationalDataset,
    detect_dataset_type,
)
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
from src.rag_config import RAGConfig
from evaluation.history import build_metrics_entry


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
    fast_model_name = os.environ.get("GEMINI_FAST_MODEL", model_name)
    qa_engine = QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        model_name=model_name,
        use_reranker=os.environ["USE_RERANKING"].lower() == "true",
        reranker_model=os.environ["RERANKER_MODEL"],
        fast_model_name=fast_model_name,
    )
    print("Components ready.")

    return embedder, vector_store, qa_engine, gemini_api_key, model_name


def get_rag_config() -> dict:
    """Read current RAG config from environment (typed values, fast-fail).

    Merges RAGConfig pipeline params with static env vars (embedding, chunk, model)
    that aren't part of the per-query pipeline config.
    """
    rag = RAGConfig.from_env()
    config = rag.to_dict()
    # Add static params that live in env but aren't per-query pipeline knobs
    config.update({
        "embedding_model": os.environ["EMBEDDING_MODEL"],
        "embedding_dim": int(os.environ["EMBEDDING_DIM"]),
        "chunk_size": int(os.environ["CHUNK_SIZE"]),
        "chunk_overlap": int(os.environ["CHUNK_OVERLAP"]),
        "fast_model": os.environ.get("GEMINI_FAST_MODEL", os.environ["GEMINI_MODEL"]),
    })
    return config


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
    rag_config = RAGConfig.from_env()
    config = get_rag_config()
    perf = PerformanceTracker()
    perf.start_suite()

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
                **rag_config.to_answer_kwargs(doc_ids=doc_ids)
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
            "decomposed": result.get("decomposed", False),
            "sub_questions": result.get("sub_questions", []),
            "retrieved_count": result.get("retrieved_count", 0),
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
            dataset, qa_engine, embedder, doc_ids
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


def run_conversational_evaluation(
    dataset: ConversationalDataset,
    qa_engine,
    embedder,
    gemini_api_key: str,
    model_name: str,
    doc_ids: list = None,
    use_judge: bool = True,
) -> dict:
    """Run evaluation on multi-turn conversations with accumulated chat history.

    Each conversation's turns are processed sequentially, building up chat_history
    exactly like the production chats endpoint (last 5 turns, 300-char truncated answers).
    """
    from google import genai

    client = genai.Client(api_key=gemini_api_key) if use_judge else None
    rag_config = RAGConfig.from_env()
    config = get_rag_config()
    perf = PerformanceTracker()
    perf.start_suite()

    conversation_results = []
    all_answer_metrics = []
    all_retrieval_metrics = []

    total_turns = dataset.total_turns
    turn_counter = 0

    print(f"\nRunning {len(dataset.conversations)} conversations ({total_turns} total turns)...")
    print(f"  LLM judge: {'ON' if use_judge else 'OFF'}")
    print(f"  Doc filter: {doc_ids if doc_ids else 'all docs'}")

    # Track scores by turn position and context dependency for conversational metrics
    scores_by_turn_pos = {}  # turn_number -> [overall scores]
    context_dep_scores = []
    context_indep_scores = []

    for conv in dataset.conversations:
        print(f"\n--- Conversation: {conv.id} ({len(conv.turns)} turns) ---")
        chat_history = []
        turn_results = []

        for turn_idx, turn in enumerate(conv.turns, 1):
            turn_counter += 1
            print(f"\n  [{turn_counter}/{total_turns}] Turn {turn_idx}: {turn.question}")

            with Timer() as total_timer:
                result = qa_engine.answer_question(
                    question=turn.question,
                    chat_history=chat_history if chat_history else None,
                    **rag_config.to_answer_kwargs(doc_ids=doc_ids)
                )

            our_answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Compute metrics (same as standalone)
            retrieval_metrics = compute_retrieval_metrics(
                sources=sources,
                expected_sources=[],  # conversational dataset doesn't use expected_sources
            )
            all_retrieval_metrics.append(retrieval_metrics)

            answer_metrics = compute_answer_metrics(
                our_answer=our_answer,
                reference_answer=turn.claude_answer,
                embedder=embedder,
                client=client if use_judge else None,
                question=turn.question,
                model_name=model_name,
            )
            all_answer_metrics.append(answer_metrics)

            perf.record(LatencyRecord(
                question_id=turn.id,
                total_ms=total_timer.elapsed_ms,
            ))

            # Build per-turn result
            turn_result = {
                "turn_id": turn.id,
                "turn_number": turn_idx,
                "conversation_id": conv.id,
                "question": turn.question,
                "difficulty": turn.difficulty,
                "category": turn.category,
                "depends_on_context": turn.depends_on_context,
                "our_answer": our_answer,
                "claude_answer": turn.claude_answer,
                "sources": sources,
                "retrieval_metrics": retrieval_metrics,
                "answer_metrics": answer_metrics,
                "latency_ms": round(total_timer.elapsed_ms, 1),
                "low_confidence": result.get("low_confidence", False),
                "chat_history_length": len(chat_history),
            }
            turn_results.append(turn_result)

            # Track conversational metrics
            overall = answer_metrics.get("llm_judge", {}).get("overall")
            if overall is not None:
                scores_by_turn_pos.setdefault(turn_idx, []).append(overall)
                if turn.depends_on_context:
                    context_dep_scores.append(overall)
                else:
                    context_indep_scores.append(overall)

            # Print quick summary
            sim = answer_metrics.get("semantic_similarity", 0)
            rl = answer_metrics.get("rouge_l", 0)
            judge_str = ""
            if overall is not None:
                judge_str = f"  Judge={overall:.1f}"
            print(f"    Sim={sim:.3f}  ROUGE-L={rl:.3f}{judge_str}  {total_timer.elapsed_ms:.0f}ms")

            # Accumulate chat history (mirrors chats.py: truncate to 300 chars, keep last 5)
            chat_history.append({
                "question": turn.question,
                "answer": our_answer[:300],
            })
            chat_history = chat_history[-5:]

        conversation_results.append({
            "conversation_id": conv.id,
            "doc_ids_hint": conv.doc_ids_hint,
            "turn_count": len(conv.turns),
            "turns": turn_results,
        })

    # Aggregate metrics
    agg_retrieval = aggregate_retrieval_metrics(all_retrieval_metrics)
    agg_answer = aggregate_answer_metrics(all_answer_metrics)
    perf_stats = perf.compute_stats()

    # Build conversational-specific metrics
    conversational_metrics = {}
    for pos, scores in sorted(scores_by_turn_pos.items()):
        conversational_metrics[f"avg_turn{pos}_score"] = round(sum(scores) / len(scores), 2)

    if 1 in scores_by_turn_pos and scores_by_turn_pos:
        max_pos = max(scores_by_turn_pos.keys())
        if max_pos > 1 and max_pos in scores_by_turn_pos:
            avg_first = sum(scores_by_turn_pos[1]) / len(scores_by_turn_pos[1])
            avg_last = sum(scores_by_turn_pos[max_pos]) / len(scores_by_turn_pos[max_pos])
            conversational_metrics["score_degradation"] = round(avg_last - avg_first, 2)

    if context_dep_scores:
        conversational_metrics["context_dependent_accuracy"] = round(
            sum(context_dep_scores) / len(context_dep_scores), 2
        )
    if context_indep_scores:
        conversational_metrics["context_independent_accuracy"] = round(
            sum(context_indep_scores) / len(context_indep_scores), 2
        )

    results = {
        "timestamp": datetime.now().isoformat(),
        "dataset": dataset.dataset_name,
        "eval_type": "conversational",
        "conversation_count": len(dataset.conversations),
        "turn_count": total_turns,
        "config": config,
        "conversations": conversation_results,
        "summary": {
            "retrieval": agg_retrieval,
            "answer_quality": agg_answer,
            "performance": perf_stats,
            "conversational": conversational_metrics,
        },
    }

    return results


def _run_ablation(dataset, qa_engine, embedder, doc_ids) -> dict:
    """Run A/B tests with features toggled on/off.

    Uses current RAGConfig as baseline — overrides one feature at a time.
    """
    rag_config = RAGConfig.from_env()
    print("\n\nRunning feature ablation...")
    ablation = {}

    configs = [
        ("no_query_expansion", {"use_query_expansion": False}),
        ("no_reranking", {"use_reranking": False}),
        ("no_adaptive_alpha", {"use_adaptive_alpha": False}),
        ("vector_only", {"use_hybrid": False, "use_query_expansion": False, "use_adaptive_alpha": False}),
    ]

    for name, overrides in configs:
        print(f"\n  Ablation: {name}")
        metrics_list = []

        for bq in dataset.questions:
            result = qa_engine.answer_question(
                question=bq.question,
                **rag_config.to_answer_kwargs(doc_ids=doc_ids, **overrides)
            )
            sources = result.get("sources", [])

            metrics = compute_retrieval_metrics(sources, bq.expected_sources)
            metrics_list.append(metrics)

        ablation[name] = aggregate_retrieval_metrics(metrics_list)
        ndcg = ablation[name].get("avg_ndcg@5", 0)
        print(f"    avg_ndcg@5 = {ndcg:.4f}")

    return ablation


def append_to_history(results: dict, output_path: str, label: str = ""):
    """Append a summary line to the eval history ledger (JSONL)."""
    history_path = Path(__file__).parent / "results" / "history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    eval_type = results.get("eval_type", "standalone")

    entry = {
        "run_id": f"{datetime.now().strftime('%Y%m%d_%H%M')}_{Path(output_path).stem[:30]}",
        "timestamp": results.get("timestamp", datetime.now().isoformat()),
        "dataset": results.get("dataset", ""),
        "eval_type": eval_type,
        "document": results.get("document", ""),
        "query_count": results.get("query_count", 0) or results.get("turn_count", 0),
        "config": results.get("config", {}),
        "metrics": build_metrics_entry(results.get("summary", {})),
        "label": label,
        "result_file": str(Path(output_path).name),
    }

    # Add conversational-specific metrics to history
    if eval_type == "conversational":
        conv_metrics = results.get("summary", {}).get("conversational", {})
        if conv_metrics:
            entry["metrics"]["conversational"] = conv_metrics

    with open(history_path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    print(f"History ledger updated: {history_path}")


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
        default=None,
        help="Output path for results (auto-generated if omitted)",
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
        "--use-judge",
        action="store_true",
        default=False,
        help="Explicitly enable LLM-as-judge (default: already on, this is a no-op for clarity)",
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
        "--label",
        default="",
        help="Label for this eval run (e.g. 'pdfplumber + adaptive alpha')",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE", "EXPERIMENT"),
        help="Compare two result files instead of running eval",
    )

    args = parser.parse_args()

    # Auto-generate output filename if not provided
    if not args.output:
        if args.compare:
            args.output = "evaluation/results/comparison.json"
        elif args.dataset:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            ds_stem = Path(args.dataset).stem[:30]
            args.output = f"evaluation/results/{ts}_{ds_stem}.json"
        else:
            args.output = "evaluation/results/eval_result.json"

    # Comparison mode
    if args.compare:
        compare_experiments(args.compare[0], args.compare[1], args.output)
        return

    # Evaluation mode
    if not args.dataset:
        parser.error("--dataset is required for evaluation mode")

    # Auto-detect dataset type
    ds_type = detect_dataset_type(args.dataset)
    is_conversational = ds_type == "conversational"

    embedder, vector_store, qa_engine, gemini_api_key, model_name = init_components()

    # Use explicit doc_ids if provided, otherwise use all docs (mirrors real user behavior)
    doc_ids = args.doc_ids
    if not doc_ids:
        doc_store_path = Path("data") / "documents.json"
        if doc_store_path.exists():
            with open(doc_store_path) as f:
                doc_ids = list(json.load(f).keys())
            print(f"  Using all {len(doc_ids)} documents (like a real user)")
        else:
            print("  WARNING: No document store found — searching unfiltered")

    if is_conversational:
        dataset = ConversationalDataset.from_file(args.dataset)
        print(f"Loaded conversational dataset: {dataset.dataset_name}")
        print(f"  Conversations: {len(dataset.conversations)}")
        print(f"  Total turns: {dataset.total_turns}")

        results = run_conversational_evaluation(
            dataset=dataset,
            qa_engine=qa_engine,
            embedder=embedder,
            gemini_api_key=gemini_api_key,
            model_name=model_name,
            doc_ids=doc_ids if doc_ids else None,
            use_judge=not args.no_judge,
        )
    else:
        dataset = BenchmarkDataset.from_file(args.dataset)
        print(f"Loaded dataset: {dataset.dataset_name}")
        print(f"  Document: {dataset.document}")
        print(f"  Questions: {len(dataset.questions)}")

        results = run_evaluation(
            dataset=dataset,
            qa_engine=qa_engine,
            embedder=embedder,
            gemini_api_key=gemini_api_key,
            model_name=model_name,
            doc_ids=doc_ids if doc_ids else None,
            use_judge=not args.no_judge,
            feature_ablation=args.ablation,
        )

    # Save JSON results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    # Append to history ledger
    append_to_history(results, str(output_path), label=args.label)

    # Console report
    console_reporter.report_summary(results)
    if is_conversational:
        turn_counter = 0
        for conv in results.get("conversations", []):
            for turn in conv.get("turns", []):
                turn_counter += 1
                console_reporter.report_query_result(turn, turn_counter)
    else:
        for i, q in enumerate(results["queries"], 1):
            console_reporter.report_query_result(q, i)

    # HTML report
    if args.html:
        html_reporter.generate_report(results, args.html)


if __name__ == "__main__":
    main()
