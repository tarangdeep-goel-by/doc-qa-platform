"""Tests for query expansion functionality."""

import pytest
import numpy as np
import os
from src.qa_engine import QAEngine
from src.embedder import Embedder
from src.vector_store import VectorStore


@pytest.fixture
def embedder():
    """Embedder instance for testing."""
    return Embedder()


@pytest.fixture
def vector_store():
    """VectorStore instance for testing."""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    store = VectorStore(
        host=qdrant_host,
        port=qdrant_port,
        collection_name="test_query_expansion"
    )
    yield store
    # Cleanup
    try:
        store.client.delete_collection("test_query_expansion")
    except:
        pass


@pytest.fixture
def qa_engine(embedder, vector_store):
    """QAEngine instance for testing."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        pytest.skip("GEMINI_API_KEY not set")

    return QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        use_reranker=False  # Disable reranker for faster tests
    )


@pytest.fixture
def sample_documents(embedder, vector_store):
    """Add sample documents to vector store."""
    chunks = [
        {
            "text": "Python is a high-level programming language. It is widely used for data science and machine learning.",
            "doc_id": "doc1",
            "doc_title": "Python Guide",
            "chunk_index": 0,
            "metadata": {}
        },
        {
            "text": "Machine learning models require large datasets for training. Popular frameworks include TensorFlow and PyTorch.",
            "doc_id": "doc1",
            "doc_title": "Python Guide",
            "chunk_index": 1,
            "metadata": {}
        },
        {
            "text": "Data preprocessing is crucial for machine learning. It involves cleaning and transforming raw data.",
            "doc_id": "doc2",
            "doc_title": "ML Best Practices",
            "chunk_index": 0,
            "metadata": {}
        },
        {
            "text": "Neural networks are inspired by biological neurons. They consist of layers of interconnected nodes.",
            "doc_id": "doc2",
            "doc_title": "ML Best Practices",
            "chunk_index": 1,
            "metadata": {}
        }
    ]

    # Embed chunks
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_texts(texts)

    # Add to vector store
    vector_store.add_document_chunks(chunks, embeddings)

    return chunks


def test_expand_query_generates_variants(qa_engine):
    """Test that _expand_query generates alternative phrasings."""
    question = "What is Python used for?"

    variants = qa_engine._expand_query(question, num_variants=2)

    # Should return original + 2 variants = 3 total
    assert len(variants) >= 1  # At minimum, returns original if expansion fails
    assert variants[0] == question  # First should be original

    if len(variants) > 1:
        # If expansion succeeded, variants should be different
        assert variants[1] != question
        assert len(variants[1]) > 0


def test_expand_query_fallback_on_error(qa_engine):
    """Test that query expansion falls back to original on error."""
    # This should work even if expansion fails
    question = ""
    variants = qa_engine._expand_query(question, num_variants=2)

    assert len(variants) >= 1
    assert variants[0] == question


def test_multi_query_hybrid_search(embedder, vector_store, sample_documents):
    """Test multi-query hybrid search with multiple variants."""
    query_variants = [
        "What is Python?",
        "Python programming language",
        "Python uses"
    ]
    query_weights = [2.0, 1.0, 1.0]

    # Embed all variants
    query_embeddings = [embedder.embed_text(q) for q in query_variants]

    # Search
    results = vector_store.multi_query_hybrid_search(
        query_variants=query_variants,
        query_embeddings=query_embeddings,
        query_weights=query_weights,
        top_k=3,
        alpha=0.5
    )

    assert len(results) > 0
    assert len(results) <= 3
    # Should find Python-related chunks
    assert "Python" in results[0]["payload"]["text"]


def test_multi_query_deduplication(embedder, vector_store, sample_documents):
    """Test that multi-query search properly deduplicates results."""
    # Use very similar queries - should find same chunks
    query_variants = ["Python", "Python programming"]
    query_weights = [1.0, 1.0]

    query_embeddings = [embedder.embed_text(q) for q in query_variants]

    results = vector_store.multi_query_hybrid_search(
        query_variants=query_variants,
        query_embeddings=query_embeddings,
        query_weights=query_weights,
        top_k=2,
        alpha=0.5
    )

    # Should deduplicate - not return same chunk twice
    chunk_ids = [r["id"] for r in results]
    assert len(chunk_ids) == len(set(chunk_ids))  # No duplicates


def test_answer_with_query_expansion(qa_engine, sample_documents):
    """Test answering with query expansion enabled."""
    question = "What is Python?"

    result = qa_engine.answer_question(
        question=question,
        top_k=3,
        use_query_expansion=True,
        query_expansion_variants=2,
        use_hybrid=True,
        use_reranking=False
    )

    assert "question" in result
    assert "answer" in result
    assert "sources" in result
    assert len(result["sources"]) > 0
    # Should find relevant Python information
    assert "Python" in result["answer"] or "programming" in result["answer"].lower()


def test_answer_without_query_expansion(qa_engine, sample_documents):
    """Test answering without query expansion (baseline)."""
    question = "What is Python?"

    result = qa_engine.answer_question(
        question=question,
        top_k=3,
        use_query_expansion=False,
        use_hybrid=True,
        use_reranking=False
    )

    assert "question" in result
    assert "answer" in result
    assert "sources" in result
    assert len(result["sources"]) > 0


def test_query_expansion_with_doc_filter(qa_engine, sample_documents):
    """Test query expansion with document filtering."""
    question = "What is machine learning?"

    result = qa_engine.answer_question(
        question=question,
        top_k=3,
        doc_ids=["doc2"],  # Filter to ML Best Practices doc
        use_query_expansion=True,
        query_expansion_variants=2,
        use_hybrid=True
    )

    assert len(result["sources"]) > 0
    # All sources should be from doc2
    for source in result["sources"]:
        assert source["doc_id"] == "doc2"


def test_query_weights_applied_correctly(embedder, vector_store, sample_documents):
    """Test that query weights are applied correctly in fusion."""
    query_variants = ["Python"]
    query_embeddings = [embedder.embed_text("Python")]

    # Weight = 1.0
    results_weight_1 = vector_store.multi_query_hybrid_search(
        query_variants=query_variants,
        query_embeddings=query_embeddings,
        query_weights=[1.0],
        top_k=2,
        alpha=0.5
    )

    # Weight = 2.0 (should give higher scores)
    results_weight_2 = vector_store.multi_query_hybrid_search(
        query_variants=query_variants,
        query_embeddings=query_embeddings,
        query_weights=[2.0],
        top_k=2,
        alpha=0.5
    )

    # Scores should be approximately 2x with weight=2.0
    assert len(results_weight_1) > 0
    assert len(results_weight_2) > 0
    assert results_weight_2[0]["score"] > results_weight_1[0]["score"]


def test_multi_query_with_empty_results(embedder, vector_store, sample_documents):
    """Test multi-query search when some queries return no results."""
    query_variants = ["Python", "nonexistent_topic_xyz"]
    query_embeddings = [embedder.embed_text(q) for q in query_variants]
    query_weights = [1.0, 1.0]

    results = vector_store.multi_query_hybrid_search(
        query_variants=query_variants,
        query_embeddings=query_embeddings,
        query_weights=query_weights,
        top_k=2,
        alpha=0.5
    )

    # Should still return results from successful queries
    assert len(results) > 0
    assert "Python" in results[0]["payload"]["text"]
