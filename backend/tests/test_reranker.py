"""Tests for cross-encoder reranker."""

import pytest
from src.reranker import Reranker


@pytest.fixture
def reranker():
    """Reranker instance for testing."""
    return Reranker()


@pytest.fixture
def sample_chunks():
    """Sample chunks with different relevance levels."""
    return [
        {
            "id": "1",
            "score": 0.8,
            "payload": {
                "text": "Python is a high-level programming language used for data science and machine learning.",
                "doc_id": "doc1",
                "doc_title": "Python Guide"
            }
        },
        {
            "id": "2",
            "score": 0.75,
            "payload": {
                "text": "JavaScript is a programming language primarily used for web development.",
                "doc_id": "doc2",
                "doc_title": "JavaScript Guide"
            }
        },
        {
            "id": "3",
            "score": 0.7,
            "payload": {
                "text": "Machine learning in Python uses libraries like scikit-learn and TensorFlow.",
                "doc_id": "doc1",
                "doc_title": "Python Guide"
            }
        },
        {
            "id": "4",
            "score": 0.65,
            "payload": {
                "text": "The Python programming language was created by Guido van Rossum in 1991.",
                "doc_id": "doc1",
                "doc_title": "Python Guide"
            }
        }
    ]


class TestReranker:
    """Test suite for Reranker."""

    def test_initialization(self, reranker):
        """Test reranker initialization."""
        assert reranker.model is not None
        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_rerank_basic(self, reranker, sample_chunks):
        """Test basic reranking functionality."""
        query = "What is Python used for in machine learning?"

        # Rerank chunks
        reranked = reranker.rerank(query, sample_chunks, top_k=3)

        # Should return top_k results
        assert len(reranked) == 3

        # Check structure
        assert "rerank_score" in reranked[0]
        assert "retrieval_score" in reranked[0]
        assert "score" in reranked[0]

        # Rerank scores should be in descending order
        scores = [r["rerank_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_improves_relevance(self, reranker, sample_chunks):
        """Test that reranking improves relevance ordering."""
        query = "machine learning in Python"

        # Rerank
        reranked = reranker.rerank(query, sample_chunks, top_k=4)

        # The chunk about "Machine learning in Python" should rank higher
        # than other chunks after reranking
        top_chunk = reranked[0]
        assert "machine learning" in top_chunk["payload"]["text"].lower()
        assert "python" in top_chunk["payload"]["text"].lower()

    def test_rerank_updates_main_score(self, reranker, sample_chunks):
        """Test that reranking updates the main score field."""
        query = "Python programming"

        reranked = reranker.rerank(query, sample_chunks, top_k=3)

        # Main score should be updated to rerank_score
        for chunk in reranked:
            assert chunk["score"] == chunk["rerank_score"]

    def test_rerank_preserves_retrieval_score(self, reranker, sample_chunks):
        """Test that original retrieval score is preserved."""
        query = "Python"

        reranked = reranker.rerank(query, sample_chunks, top_k=3)

        # Original scores should be preserved
        original_scores = {c["id"]: c["score"] for c in sample_chunks}
        for chunk in reranked:
            chunk_id = chunk["id"]
            assert chunk["retrieval_score"] == original_scores[chunk_id]

    def test_rerank_empty_chunks(self, reranker):
        """Test reranking with empty chunks list."""
        query = "test query"

        reranked = reranker.rerank(query, [], top_k=5)

        assert len(reranked) == 0

    def test_rerank_top_k_limit(self, reranker, sample_chunks):
        """Test that top_k limit is respected."""
        query = "Python"

        # Request only 2 results
        reranked = reranker.rerank(query, sample_chunks, top_k=2)

        assert len(reranked) == 2

    def test_rerank_top_k_larger_than_chunks(self, reranker, sample_chunks):
        """Test top_k larger than available chunks."""
        query = "Python"

        # Request more than available
        reranked = reranker.rerank(query, sample_chunks, top_k=10)

        # Should return all chunks
        assert len(reranked) == len(sample_chunks)

    def test_rerank_single_chunk(self, reranker):
        """Test reranking with single chunk."""
        query = "Python programming"
        chunk = [{
            "id": "1",
            "score": 0.8,
            "payload": {
                "text": "Python is great for programming."
            }
        }]

        reranked = reranker.rerank(query, chunk, top_k=1)

        assert len(reranked) == 1
        assert "rerank_score" in reranked[0]

    def test_rerank_preserves_metadata(self, reranker, sample_chunks):
        """Test that reranking preserves all chunk metadata."""
        query = "Python"

        reranked = reranker.rerank(query, sample_chunks, top_k=3)

        # Check that all original fields are preserved
        for chunk in reranked:
            assert "id" in chunk
            assert "payload" in chunk
            assert "doc_id" in chunk["payload"]
            assert "doc_title" in chunk["payload"]
            assert "text" in chunk["payload"]

    def test_rerank_score_range(self, reranker, sample_chunks):
        """Test that rerank scores are reasonable."""
        query = "Python machine learning"

        reranked = reranker.rerank(query, sample_chunks, top_k=4)

        # Rerank scores should be floats
        for chunk in reranked:
            assert isinstance(chunk["rerank_score"], float)
            # Scores can be negative or positive depending on the model
            # Just check they're reasonable numbers
            assert -100 < chunk["rerank_score"] < 100

    def test_rerank_different_queries_different_scores(self, reranker, sample_chunks):
        """Test that different queries produce different rankings."""
        query1 = "Python programming language"
        query2 = "JavaScript web development"

        reranked1 = reranker.rerank(query1, sample_chunks, top_k=3)
        reranked2 = reranker.rerank(query2, sample_chunks, top_k=3)

        # Top results should be different for different queries
        top1_text = reranked1[0]["payload"]["text"]
        top2_text = reranked2[0]["payload"]["text"]

        # Python query should rank Python chunks higher
        assert "python" in top1_text.lower()
        # JavaScript query should rank JavaScript chunks higher
        assert "javascript" in top2_text.lower()

    def test_rerank_chunks_without_payload(self, reranker):
        """Test reranking chunks with different structure (no payload field)."""
        query = "test query"
        chunks = [
            {
                "id": "1",
                "score": 0.8,
                "text": "This is a test chunk"
            },
            {
                "id": "2",
                "score": 0.7,
                "text": "Another test chunk"
            }
        ]

        reranked = reranker.rerank(query, chunks, top_k=2)

        # Should still work and return results
        assert len(reranked) == 2
        assert "rerank_score" in reranked[0]

    def test_rerank_long_query(self, reranker, sample_chunks):
        """Test reranking with a long query."""
        query = "I want to learn about Python programming language and how it is used in machine learning and data science applications with libraries like TensorFlow"

        reranked = reranker.rerank(query, sample_chunks, top_k=3)

        assert len(reranked) == 3
        # Should rank machine learning + Python chunk high
        assert any("machine learning" in c["payload"]["text"].lower()
                   for c in reranked[:2])
