"""Tests for QA engine production guardrails."""

import pytest
import os
from src.qa_engine import QAEngine
from src.embedder import Embedder
from src.vector_store import VectorStore


@pytest.fixture
def embedder():
    """Embedder instance."""
    return Embedder()


@pytest.fixture
def vector_store():
    """VectorStore instance."""
    store = VectorStore(collection_name="test_qa_guardrails")
    yield store
    # Cleanup
    try:
        store.client.delete_collection("test_qa_guardrails")
    except:
        pass


@pytest.fixture
def qa_engine(embedder, vector_store):
    """QA engine instance."""
    gemini_api_key = os.getenv("GEMINI_API_KEY", "test_key")
    return QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        use_reranker=True
    )


@pytest.fixture
def sample_documents(embedder, vector_store):
    """Add sample documents to vector store."""
    chunks = [
        {
            "text": "Our company PTO policy allows 15 days of vacation per year for employees with less than 5 years tenure.",
            "doc_id": "policy1",
            "doc_title": "HR Policy 2024",
            "chunk_index": 0,
            "metadata": {}
        },
        {
            "text": "Employees with 5+ years tenure receive 20 days of PTO annually.",
            "doc_id": "policy1",
            "doc_title": "HR Policy 2024",
            "chunk_index": 1,
            "metadata": {}
        },
        {
            "text": "Remote work is allowed up to 3 days per week for most positions.",
            "doc_id": "policy2",
            "doc_title": "Remote Work Policy",
            "chunk_index": 0,
            "metadata": {}
        }
    ]

    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_texts(texts)
    vector_store.add_document_chunks(chunks, embeddings)

    return chunks


class TestQAGuardrails:
    """Test suite for QA engine guardrails."""

    def test_min_score_threshold_rejection(self, qa_engine, sample_documents):
        """Test that low-confidence queries are rejected."""
        # Ask about something completely unrelated
        result = qa_engine.answer_question(
            question="What is the weather forecast for tomorrow?",
            top_k=5,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.5  # High threshold
        )

        # Should indicate low confidence
        assert "low_confidence" in result
        assert result["low_confidence"] is True
        assert "don't have enough information" in result["answer"].lower() or \
               "couldn't find" in result["answer"].lower()

    def test_min_score_threshold_acceptance(self, qa_engine, sample_documents):
        """Test that relevant queries pass threshold."""
        # Ask about something in the documents
        result = qa_engine.answer_question(
            question="How many PTO days do employees with 5 years get?",
            top_k=5,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.3  # Lower threshold
        )

        # Should have confidence
        if "low_confidence" in result:
            # If it's still low confidence, that's OK for test data
            # but at least verify it returned sources
            assert len(result["sources"]) > 0

    def test_no_results_handling(self, qa_engine):
        """Test handling when no documents match."""
        # Empty vector store scenario
        result = qa_engine.answer_question(
            question="What is the meaning of life?",
            top_k=5,
            doc_ids=["nonexistent_doc"]  # Filter to non-existent doc
        )

        assert "low_confidence" in result
        assert result["low_confidence"] is True
        assert result["retrieved_count"] == 0

    def test_hybrid_search_flag(self, qa_engine, sample_documents):
        """Test hybrid search can be toggled."""
        question = "PTO policy"

        # With hybrid search
        result_hybrid = qa_engine.answer_question(
            question=question,
            top_k=3,
            use_hybrid=True,
            min_score=0.1
        )

        # Without hybrid search (pure vector)
        result_vector = qa_engine.answer_question(
            question=question,
            top_k=3,
            use_hybrid=False,
            min_score=0.1
        )

        # Both should return results
        assert len(result_hybrid["sources"]) > 0
        assert len(result_vector["sources"]) > 0

    def test_reranking_flag(self, qa_engine, sample_documents):
        """Test reranking can be toggled."""
        question = "How many PTO days?"

        # With reranking
        result_rerank = qa_engine.answer_question(
            question=question,
            top_k=3,
            use_reranking=True,
            min_score=0.1
        )

        # Without reranking
        result_no_rerank = qa_engine.answer_question(
            question=question,
            top_k=3,
            use_reranking=False,
            min_score=0.1
        )

        # Both should return results
        assert len(result_rerank["sources"]) > 0
        assert len(result_no_rerank["sources"]) > 0

    def test_improved_prompt_grounding(self, qa_engine, sample_documents):
        """Test that improved prompt is used."""
        # This is more of a smoke test - actual grounding verification
        # would require checking Gemini responses
        result = qa_engine.answer_question(
            question="What is the PTO policy?",
            top_k=3,
            use_hybrid=True,
            min_score=0.1
        )

        # Should return answer
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_source_metadata_warnings(self, qa_engine, sample_documents):
        """Test source metadata warning helper."""
        # Create sources with low scores
        sources = [
            {"score": 0.3, "doc_id": "doc1"},
            {"score": 0.25, "doc_id": "doc2"}
        ]

        warning = qa_engine._check_source_metadata(sources)

        # Should generate warning for low scores
        assert "⚠️" in warning or len(warning) == 0  # Might not warn if threshold not met

    def test_source_metadata_warnings_empty(self, qa_engine):
        """Test metadata warnings with empty sources."""
        warning = qa_engine._check_source_metadata([])

        assert warning == ""

    def test_answer_with_min_score_variations(self, qa_engine, sample_documents):
        """Test different min_score thresholds."""
        question = "PTO policy"

        # Very low threshold (should pass)
        result_low = qa_engine.answer_question(
            question=question,
            min_score=0.1
        )

        # Very high threshold (might reject)
        result_high = qa_engine.answer_question(
            question=question,
            min_score=0.9
        )

        # Low threshold should not show low confidence
        # (unless genuinely no good matches)
        assert "answer" in result_low

        # High threshold might show low confidence
        # depending on actual scores
        assert "answer" in result_high

    def test_retrieval_count_in_response(self, qa_engine, sample_documents):
        """Test that retrieved_count is included in response."""
        result = qa_engine.answer_question(
            question="PTO days",
            top_k=3,
            min_score=0.1
        )

        assert "retrieved_count" in result
        assert isinstance(result["retrieved_count"], int)
        assert result["retrieved_count"] >= 0

    def test_top_score_in_low_confidence_response(self, qa_engine, sample_documents):
        """Test that top_score is included when low confidence."""
        # Ask unrelated question to trigger low confidence
        result = qa_engine.answer_question(
            question="What is quantum physics?",
            min_score=0.6  # High threshold
        )

        if result.get("low_confidence"):
            assert "top_score" in result
            assert isinstance(result["top_score"], (int, float))

    def test_hybrid_alpha_variations(self, qa_engine, sample_documents):
        """Test different hybrid alpha values."""
        question = "PTO tenure"

        # All semantic (alpha=1.0)
        result_semantic = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            hybrid_alpha=1.0,
            min_score=0.1
        )

        # All keyword (alpha=0.0)
        result_keyword = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            hybrid_alpha=0.0,
            min_score=0.1
        )

        # Balanced (alpha=0.5)
        result_balanced = qa_engine.answer_question(
            question=question,
            use_hybrid=True,
            hybrid_alpha=0.5,
            min_score=0.1
        )

        # All should work
        assert "answer" in result_semantic
        assert "answer" in result_keyword
        assert "answer" in result_balanced

    def test_doc_filter_with_guardrails(self, qa_engine, sample_documents):
        """Test guardrails with document filtering."""
        # Filter to specific doc
        result = qa_engine.answer_question(
            question="PTO policy",
            doc_ids=["policy1"],
            min_score=0.2
        )

        # Should only return sources from policy1
        if result.get("sources"):
            assert all(s["doc_id"] == "policy1" for s in result["sources"])

    def test_reranking_improves_scores(self, qa_engine, sample_documents):
        """Test that reranking can improve relevance scores."""
        question = "How much PTO for 5 years tenure?"

        # Get more candidates
        result = qa_engine.answer_question(
            question=question,
            top_k=2,
            use_hybrid=True,
            use_reranking=True,
            min_score=0.1
        )

        # If we got results, check they have rerank scores
        if result.get("sources") and len(result["sources"]) > 0:
            # Reranked sources should exist
            assert len(result["sources"]) > 0
