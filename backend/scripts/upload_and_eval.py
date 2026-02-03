#!/usr/bin/env python3
"""
One-command script to upload a document, inspect chunks, run benchmark queries,
and log everything.

Usage:
    python scripts/upload_and_eval.py path/to/doc.pdf \
        --benchmark evaluation/datasets/fx5u_qa_benchmark.json \
        --output evaluation/results/baseline.json

    # Use existing document (skip upload):
    python scripts/upload_and_eval.py --doc-id <existing-doc-id> \
        --benchmark evaluation/datasets/fx5u_qa_benchmark.json \
        --output evaluation/results/baseline.json

    # Quick mode (no LLM judge, no ablation):
    python scripts/upload_and_eval.py path/to/doc.pdf \
        --benchmark evaluation/datasets/fx5u_qa_benchmark.json \
        --output evaluation/results/quick.json \
        --no-judge
"""

import argparse
import json
import os
import random
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")


def upload_document(file_path: str, base_url: str) -> dict:
    """Upload a document via the API and return response."""
    import requests

    print(f"\n1. Uploading document: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "application/pdf")}
        response = requests.post(f"{base_url}/api/admin/upload", files=files)

    if response.status_code != 200:
        print(f"   Upload failed: {response.status_code} - {response.text}")
        sys.exit(1)

    data = response.json()
    print(f"   Document ID: {data['doc_id']}")
    print(f"   Chunks: {data.get('chunk_count', '?')}")
    return data


def inspect_chunks(doc_id: str, vector_store, sample_size: int = 5) -> dict:
    """Inspect chunks for a document - count, size distribution, samples."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    print(f"\n2. Inspecting chunks for doc_id={doc_id}")

    # Scroll all chunks for this document
    all_chunks = []
    offset = None

    while True:
        result = vector_store.client.scroll(
            collection_name=vector_store.collection_name,
            limit=100,
            offset=offset,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
                ]
            ),
            with_payload=True,
            with_vectors=False,
        )
        points, offset = result
        if not points:
            break
        all_chunks.extend(points)
        if offset is None:
            break

    chunk_count = len(all_chunks)
    print(f"   Total chunks: {chunk_count}")

    if chunk_count == 0:
        return {"chunk_count": 0}

    # Size distribution
    sizes = [len(p.payload.get("text", "")) for p in all_chunks]
    size_stats = {
        "min": min(sizes),
        "max": max(sizes),
        "mean": round(statistics.mean(sizes)),
        "median": round(statistics.median(sizes)),
        "p95": round(sorted(sizes)[int(len(sizes) * 0.95)]) if len(sizes) >= 20 else max(sizes),
    }
    print(f"   Size distribution: min={size_stats['min']}, max={size_stats['max']}, "
          f"mean={size_stats['mean']}, median={size_stats['median']}")

    # Sample chunks
    sample = random.sample(all_chunks, min(sample_size, chunk_count))
    samples = []
    for p in sample:
        text = p.payload.get("text", "")
        samples.append({
            "chunk_index": p.payload.get("chunk_index"),
            "page_num": p.payload.get("page_num"),
            "text_length": len(text),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
        })
        print(f"   Sample chunk #{p.payload.get('chunk_index', '?')} "
              f"(page {p.payload.get('page_num', '?')}, {len(text)} chars): "
              f"{text[:80]}...")

    return {
        "chunk_count": chunk_count,
        "chunk_size_stats": size_stats,
        "sample_chunks": samples,
    }


def run_benchmark_queries(
    dataset,
    qa_engine,
    embedder,
    doc_ids: list,
    gemini_api_key: str,
    model_name: str,
    use_judge: bool = True,
) -> list:
    """Run all benchmark questions and collect results."""
    from google import genai
    from evaluation.metrics.retrieval import compute_retrieval_metrics
    from evaluation.metrics.answer_quality import compute_answer_metrics
    from evaluation.metrics.performance import Timer

    client = genai.Client(api_key=gemini_api_key) if use_judge else None

    top_k = int(os.environ["TOP_K_RESULTS"])
    use_hybrid = os.environ["USE_HYBRID_SEARCH"].lower() == "true"
    hybrid_alpha = float(os.environ["HYBRID_ALPHA"])
    use_reranking = os.environ["USE_RERANKING"].lower() == "true"
    use_query_expansion = os.environ["USE_QUERY_EXPANSION"].lower() == "true"
    query_expansion_variants = int(os.environ["QUERY_EXPANSION_VARIANTS"])
    use_rrf = os.environ["USE_RRF"].lower() == "true"
    rerank_blending = os.environ["RERANKER_BLENDING"]

    results = []

    print(f"\n3. Running {len(dataset.questions)} benchmark queries...")

    for i, bq in enumerate(dataset.questions, 1):
        print(f"\n   [{i}/{len(dataset.questions)}] {bq.question}")

        with Timer() as t:
            answer_result = qa_engine.answer_question(
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

        our_answer = answer_result.get("answer", "")
        sources = answer_result.get("sources", [])

        # Retrieval metrics
        retrieval_metrics = compute_retrieval_metrics(
            sources=sources,
            expected_sources=bq.expected_sources,
        )

        # Answer quality metrics
        answer_metrics = compute_answer_metrics(
            our_answer=our_answer,
            reference_answer=bq.claude_answer,
            embedder=embedder,
            client=client if use_judge else None,
            question=bq.question,
            model_name=model_name,
        )

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
            "latency_ms": round(t.elapsed_ms, 1),
            "retrieved_count": answer_result.get("retrieved_count", 0),
            "low_confidence": answer_result.get("low_confidence", False),
        }
        results.append(query_result)

        # Quick summary
        ndcg = retrieval_metrics.get("ndcg@5", 0)
        sim = answer_metrics.get("semantic_similarity", 0)
        print(f"   NDCG@5={ndcg:.3f}  Sim={sim:.3f}  ROUGE-L={answer_metrics.get('rouge_l', 0):.3f}  "
              f"{t.elapsed_ms:.0f}ms")

    return results


def build_output(
    document_info: dict,
    chunk_info: dict,
    query_results: list,
    config: dict,
) -> dict:
    """Assemble the full output JSON."""
    from evaluation.metrics.retrieval import aggregate_retrieval_metrics
    from evaluation.metrics.answer_quality import aggregate_answer_metrics

    # Aggregate metrics
    retrieval_list = [q["retrieval_metrics"] for q in query_results]
    answer_list = [q["answer_metrics"] for q in query_results]

    agg_retrieval = aggregate_retrieval_metrics(retrieval_list)
    agg_answer = aggregate_answer_metrics(answer_list)

    latencies = [q["latency_ms"] for q in query_results]
    avg_latency = statistics.mean(latencies) if latencies else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "document": document_info,
        "chunks": chunk_info,
        "config": config,
        "queries": query_results,
        "summary": {
            "retrieval": agg_retrieval,
            "answer_quality": agg_answer,
            "performance": {
                "query_count": len(query_results),
                "latency_ms": {
                    "mean": round(avg_latency, 1),
                    "min": round(min(latencies), 1) if latencies else 0,
                    "max": round(max(latencies), 1) if latencies else 0,
                },
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Upload document + run evaluation benchmark"
    )
    parser.add_argument("file_path", nargs="?", help="Path to PDF file to upload")
    parser.add_argument(
        "--doc-id", help="Use existing document ID (skip upload)"
    )
    parser.add_argument(
        "--benchmark",
        required=True,
        help="Path to benchmark dataset JSON",
    )
    parser.add_argument(
        "--output",
        default="evaluation/results/upload_eval.json",
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip LLM-as-judge",
    )
    parser.add_argument(
        "--html",
        help="Also generate HTML report at this path",
    )

    args = parser.parse_args()

    if not args.file_path and not args.doc_id:
        parser.error("Either file_path or --doc-id is required")

    # Load benchmark dataset
    from evaluation.benchmark_dataset import BenchmarkDataset

    dataset = BenchmarkDataset.from_file(args.benchmark)
    print(f"Loaded benchmark: {dataset.dataset_name} ({len(dataset.questions)} questions)")

    # Initialize components
    from src.embedder import Embedder
    from src.vector_store import VectorStore
    from src.qa_engine import QAEngine

    embedding_model = os.environ["EMBEDDING_MODEL"]
    qdrant_host = os.environ["QDRANT_HOST"]
    qdrant_port = int(os.environ["QDRANT_PORT"])
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    model_name = os.environ["GEMINI_MODEL"]
    embedding_dim = int(os.environ["EMBEDDING_DIM"])

    print("\nInitializing components...")
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

    # Step 1: Upload or use existing document
    if args.doc_id:
        doc_id = args.doc_id
        document_info = {"doc_id": doc_id, "source": "existing"}
        print(f"\nUsing existing document: {doc_id}")
    else:
        upload_result = upload_document(args.file_path, args.base_url)
        doc_id = upload_result["doc_id"]
        document_info = {
            "doc_id": doc_id,
            "filename": Path(args.file_path).name,
            "chunk_count": upload_result.get("chunk_count"),
            "source": "uploaded",
        }

    # Step 2: Inspect chunks
    chunk_info = inspect_chunks(doc_id, vector_store)

    # Step 3: Run benchmark queries
    query_results = run_benchmark_queries(
        dataset=dataset,
        qa_engine=qa_engine,
        embedder=embedder,
        doc_ids=[doc_id],
        gemini_api_key=gemini_api_key,
        model_name=model_name,
        use_judge=not args.no_judge,
    )

    # Step 4: Build and save output
    from evaluation.run_evaluation import get_rag_config

    config = get_rag_config()
    output = build_output(document_info, chunk_info, query_results, config)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n4. Results saved to: {output_path}")

    # Console summary
    from evaluation.reporters import console_reporter

    console_reporter.report_summary(output)

    # HTML report
    if args.html:
        from evaluation.reporters import html_reporter

        html_reporter.generate_report(output, args.html, title="Upload & Eval Report")

    print("\nDone.")


if __name__ == "__main__":
    main()
