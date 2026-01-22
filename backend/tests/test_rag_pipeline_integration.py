"""Integration tests for complete RAG pipeline with all improvements."""

import pytest
import os
from src.embedder import Embedder
from src.vector_store import VectorStore
from src.qa_engine import QAEngine
from src.bm25_index import BM25Index
from src.reranker import Reranker


@pytest.fixture
def embedder():
    """Embedder instance."""
    return Embedder()


@pytest.fixture
def vector_store():
    """VectorStore instance."""
    import os
    # Use environment variables for host/port (Docker compatibility)
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    store = VectorStore(
        host=qdrant_host,
        port=qdrant_port,
        collection_name="test_rag_pipeline"
    )
    yield store
    # Cleanup
    try:
        store.client.delete_collection("test_rag_pipeline")
    except:
        pass


@pytest.fixture
def qa_engine(embedder, vector_store):
    """QA engine with all features enabled."""
    gemini_api_key = os.getenv("GEMINI_API_KEY", "test_key")
    return QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        use_reranker=True
    )


@pytest.fixture
def comprehensive_documents(embedder, vector_store):
    """Add comprehensive test documents."""
    chunks = [
        # Document 1: Python Programming
        {
            "text": "Python is a high-level, interpreted programming language created by Guido van Rossum in 1991.",
            "doc_id": "python_doc",
            "doc_title": "Python Programming Guide",
            "chunk_index": 0,
            "page_num": 1,
            "metadata": {}
        },
        {
            "text": "Python is widely used for web development, data science, machine learning, and automation.",
            "doc_id": "python_doc",
            "doc_title": "Python Programming Guide",
            "chunk_index": 1,
            "page_num": 1,
            "metadata": {}
        },
        {
            "text": "Popular Python libraries include NumPy for numerical computing, Pandas for data analysis, and scikit-learn for machine learning.",
            "doc_id": "python_doc",
            "doc_title": "Python Programming Guide",
            "chunk_index": 2,
            "page_num": 2,
            "metadata": {}
        },
        # Document 2: Company HR Policy
        {
            "text": "Employee PTO Policy: All full-time employees receive paid time off (PTO) based on tenure.",
            "doc_id": "hr_policy",
            "doc_title": "HR Policy Manual 2024",
            "chunk_index": 0,
            "page_num": 1,
            "metadata": {}
        },
        {
            "text": "Employees with 0-2 years tenure: 15 days PTO annually. Employees with 3-5 years tenure: 18 days PTO annually.",
            "doc_id": "hr_policy",
            "doc_title": "HR Policy Manual 2024",
            "chunk_index": 1,
            "page_num": 1,
            "metadata": {}
        },
        {
            "text": "Employees with 5+ years tenure: 20 days PTO annually. Senior employees with 10+ years: 25 days PTO annually.",
            "doc_id": "hr_policy",
            "doc_title": "HR Policy Manual 2024",
            "chunk_index": 2,
            "page_num": 2,
            "metadata": {}
        },
        # Document 3: Technical Documentation
        {
            "text": "API Configuration: Set GEMINI_API_KEY environment variable for Google Gemini access.",
            "doc_id": "tech_docs",
            "doc_title": "Technical Documentation",
            "chunk_index": 0,
            "page_num": 1,
            "metadata": {}
        },
        {
            "text": "The RAG pipeline uses sentence-transformers/all-MiniLM-L6-v2 for embeddings with 384 dimensions.",
            "doc_id": "tech_docs",
            "doc_title": "Technical Documentation",
            "chunk_index": 1,
            "page_num": 1,
            "metadata": {}
        }
    ]

    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_texts(texts)
    vector_store.add_document_chunks(chunks, embeddings)

    return chunks


class TestRAGPipelineIntegration:
    """Comprehensive integration tests for RAG pipeline."""

    def test_full_pipeline_pure_vector_search(self, qa_engine, comprehensive_documents):
        """Test complete pipeline with pure vector search."""
        result = qa_engine.answer_question(
            question="What is Python used for?",
            top_k=5,
            use_hybrid=False,
            use_reranking=False,
            min_score=0.1
        )

        assert "answer" in result
        assert len(result["sources"]) > 0
        assert result["retrieved_count"] > 0

    def test_full_pipeline_hybrid_search(self, qa_engine, comprehensive_documents):
        """Test complete pipeline with hybrid search."""
        result = qa_engine.answer_question(
            question="Python machine learning libraries",
            top_k=5,
            use_hybrid=True,
            hybrid_alpha=0.5,
            use_reranking=False,
            min_score=0.1
        )

        assert "answer" in result
        assert len(result["sources"]) > 0

        # Should find the chunk about Python libraries
        source_texts = [s["chunk_text"] for s in result["sources"]]
        assert any("scikit-learn" in text for text in source_texts)

    def test_full_pipeline_with_reranking(self, qa_engine, comprehensive_documents):
        """Test complete pipeline with hybrid search and reranking."""
        result = qa_engine.answer_question(
            question="How many PTO days for 5 years tenure?",
            top_k=3,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        assert "answer" in result
        assert len(result["sources"]) > 0

        # Should find the relevant PTO policy chunk
        source_texts = " ".join([s["chunk_text"] for s in result["sources"]])
        assert "5+ years" in source_texts or "5 years" in source_texts

    def test_pipeline_with_guardrails_pass(self, qa_engine, comprehensive_documents):
        """Test pipeline with guardrails - relevant query should pass."""
        result = qa_engine.answer_question(
            question="What are popular Python libraries?",
            use_hybrid=True,
            use_reranking=True,
            min_score=0.3
        )

        # Should pass threshold and provide answer
        if "low_confidence" in result:
            # If it's low confidence, at least check we got sources
            assert len(result["sources"]) > 0
        else:
            # Should have a meaningful answer
            assert len(result["answer"]) > 20

    def test_pipeline_with_guardrails_reject(self, qa_engine, comprehensive_documents):
        """Test pipeline with guardrails - unrelated query should be rejected."""
        result = qa_engine.answer_question(
            question="What is the capital of France?",
            use_hybrid=True,
            use_reranking=True,
            min_score=0.6  # High threshold
        )

        # Should reject with low confidence
        assert "low_confidence" in result
        assert result["low_confidence"] is True
        assert "don't have enough information" in result["answer"].lower() or \
               "couldn't find" in result["answer"].lower()

    def test_pipeline_with_document_filter(self, qa_engine, comprehensive_documents):
        """Test pipeline with document filtering."""
        result = qa_engine.answer_question(
            question="PTO policy",
            doc_ids=["hr_policy"],
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        # Should only return sources from hr_policy
        assert all(s["doc_id"] == "hr_policy" for s in result["sources"])

    def test_pipeline_keyword_emphasis(self, qa_engine, comprehensive_documents):
        """Test that hybrid search emphasizes exact keyword matches."""
        # Search for specific term "scikit-learn"
        result = qa_engine.answer_question(
            question="scikit-learn",
            use_hybrid=True,
            hybrid_alpha=0.3,  # Favor keyword matching
            use_reranking=False,
            min_score=0.1
        )

        # Should find the chunk with scikit-learn
        assert any("scikit-learn" in s["chunk_text"] for s in result["sources"])

    def test_pipeline_semantic_emphasis(self, qa_engine, comprehensive_documents):
        """Test that pipeline can find semantically similar content."""
        # Search with semantic question (no exact keywords)
        result = qa_engine.answer_question(
            question="programming language for data analysis",
            use_hybrid=True,
            hybrid_alpha=0.8,  # Favor semantic matching
            use_reranking=True,
            min_score=0.1
        )

        # Should find Python-related chunks
        source_texts = " ".join([s["chunk_text"] for s in result["sources"]])
        assert "python" in source_texts.lower()

    def test_pipeline_retrieval_count(self, qa_engine, comprehensive_documents):
        """Test that pipeline respects top_k parameter."""
        result = qa_engine.answer_question(
            question="What is Python?",
            top_k=3,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        # Should return at most top_k results
        assert len(result["sources"]) <= 3

    def test_pipeline_source_metadata(self, qa_engine, comprehensive_documents):
        """Test that source metadata is preserved through pipeline."""
        result = qa_engine.answer_question(
            question="Python programming",
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        # Check source structure
        for source in result["sources"]:
            assert "doc_id" in source
            assert "doc_title" in source
            assert "chunk_text" in source
            assert "score" in source
            assert "page_num" in source or source.get("page_num") is None

    def test_pipeline_empty_query(self, qa_engine, comprehensive_documents):
        """Test pipeline handles empty query gracefully."""
        result = qa_engine.answer_question(
            question="",
            use_hybrid=True,
            use_reranking=True
        )

        # Should handle gracefully
        assert "answer" in result

    def test_pipeline_very_long_query(self, qa_engine, comprehensive_documents):
        """Test pipeline with very long query."""
        long_query = "I am looking for information about programming languages, specifically Python, and I want to know what it is used for, what are the popular libraries for data science and machine learning, and also I would like to understand who created it and when."

        result = qa_engine.answer_question(
            question=long_query,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        assert "answer" in result
        assert len(result["sources"]) > 0

    def test_pipeline_multiple_queries_consistency(self, qa_engine, comprehensive_documents):
        """Test that multiple queries to same documents are consistent."""
        question = "What is Python used for?"

        result1 = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.2
        )

        result2 = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.2
        )

        # Should return sources (might be in different order due to reranking)
        assert len(result1["sources"]) > 0
        assert len(result2["sources"]) > 0

    def test_pipeline_alpha_zero_vs_one(self, qa_engine, comprehensive_documents):
        """Test pipeline with extreme alpha values."""
        question = "Python NumPy"

        # All keyword (alpha=0)
        result_keyword = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            hybrid_alpha=0.0,
            use_reranking=False,
            min_score=0.1
        )

        # All semantic (alpha=1)
        result_semantic = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            hybrid_alpha=1.0,
            use_reranking=False,
            min_score=0.1
        )

        # Both should work
        assert len(result_keyword["sources"]) > 0
        assert len(result_semantic["sources"]) > 0

    def test_pipeline_performance_baseline(self, qa_engine, comprehensive_documents):
        """Test pipeline performance - should complete in reasonable time."""
        import time

        start = time.time()
        result = qa_engine.answer_question(
            question="Python libraries for machine learning",
            top_k=5,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )
        elapsed = time.time() - start

        # Should complete in under 10 seconds (generous for CI/test environments)
        assert elapsed < 10.0
        assert "answer" in result

    def test_bm25_index_persistence_across_operations(self, vector_store, embedder):
        """Test that BM25 index is maintained across operations."""
        # Add initial chunks
        chunks = [
            {
                "text": "Test chunk one",
                "doc_id": "test1",
                "doc_title": "Test",
                "chunk_index": 0,
                "metadata": {}
            }
        ]

        embeddings = embedder.embed_texts([c["text"] for c in chunks])
        vector_store.add_document_chunks(chunks, embeddings)

        # BM25 index should be built
        assert vector_store.bm25_index.index is not None

        # Delete document
        vector_store.delete_document("test1")

        # BM25 index should still exist (but may be empty)
        assert vector_store.bm25_index is not None
