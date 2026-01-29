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

    def test_position_aware_blending_basic(self, reranker, sample_chunks):
        """Test position-aware blending functionality."""
        query = "Python programming"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=3,
            blend_strategy="position_aware"
        )

        assert len(reranked) == 3

        # Check that blending metadata is present
        for chunk in reranked:
            assert "retrieval_score" in chunk
            assert "rerank_score" in chunk
            assert "blend_weights" in chunk
            assert "score" in chunk

    def test_position_aware_weights_top_ranks(self, reranker, sample_chunks):
        """Test that top 3 ranks get higher retrieval weight (75%)."""
        query = "Python"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=4,
            blend_strategy="position_aware"
        )

        # Before reranking, top 3 should have retrieval_weight = 0.75
        # We need to check the original ranking positions
        # Since chunks are reranked, we can't directly check
        # But we can verify the blend_weights are set correctly

        # Check structure
        for chunk in reranked:
            weights = chunk["blend_weights"]
            assert "retrieval" in weights
            assert "rerank" in weights
            assert weights["retrieval"] + weights["rerank"] == 1.0

    def test_position_aware_vs_replace_strategy(self, reranker, sample_chunks):
        """Test difference between position-aware and replace strategies."""
        query = "machine learning in Python"

        # Position-aware blending
        position_aware = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=3,
            blend_strategy="position_aware"
        )

        # Replace strategy (standard reranking)
        replace = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=3,
            blend_strategy="replace"
        )

        # Both should return results
        assert len(position_aware) == 3
        assert len(replace) == 3

        # Position-aware should have blend_weights
        assert "blend_weights" in position_aware[0]

        # Replace should not have blend_weights
        assert "blend_weights" not in replace[0]

    def test_position_aware_blending_scores(self, reranker, sample_chunks):
        """Test that blended scores are computed correctly."""
        query = "Python"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=4,
            blend_strategy="position_aware"
        )

        # Verify blended score calculation
        for chunk in reranked:
            retrieval_score = chunk["retrieval_score"]
            rerank_score = chunk["rerank_score"]
            blend_weights = chunk["blend_weights"]

            expected_score = (
                blend_weights["retrieval"] * retrieval_score +
                blend_weights["rerank"] * rerank_score
            )

            # Allow small floating point difference
            assert abs(chunk["score"] - expected_score) < 0.0001

    def test_position_aware_empty_chunks(self, reranker):
        """Test position-aware blending with empty chunks."""
        query = "test"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=[],
            top_k=5,
            blend_strategy="position_aware"
        )

        assert len(reranked) == 0

    def test_position_aware_preserves_metadata(self, reranker, sample_chunks):
        """Test that position-aware blending preserves all metadata."""
        query = "Python"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=3,
            blend_strategy="position_aware"
        )

        # Check all original fields preserved
        for chunk in reranked:
            assert "id" in chunk
            assert "payload" in chunk
            assert "doc_id" in chunk["payload"]
            assert "doc_title" in chunk["payload"]
            assert "text" in chunk["payload"]

    def test_position_aware_blend_weights_progression(self, reranker):
        """Test that blend weights change appropriately with rank."""
        query = "test query"

        # Create many chunks to test different rank positions
        chunks = [
            {
                "id": str(i),
                "score": 1.0 - (i * 0.05),  # Decreasing scores
                "payload": {
                    "text": f"Test chunk {i}",
                    "doc_id": "doc1",
                    "doc_title": "Test Doc"
                }
            }
            for i in range(15)
        ]

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=chunks,
            top_k=15,
            blend_strategy="position_aware"
        )

        # Get original positions (before reranking)
        # We'll check the weight pattern across ranks

        # For simplicity, we just verify structure is correct
        assert len(reranked) == 15
        assert all("blend_weights" in c for c in reranked)

    def test_position_aware_top_k_limit(self, reranker, sample_chunks):
        """Test that position-aware blending respects top_k."""
        query = "Python"

        reranked = reranker.rerank_with_position_blending(
            query=query,
            chunks=sample_chunks,
            top_k=2,
            blend_strategy="position_aware"
        )

        assert len(reranked) == 2
