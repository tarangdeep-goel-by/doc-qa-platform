"""Tests for BM25 keyword search index."""

import pytest
import os
import shutil
from src.bm25_index import BM25Index


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "text": "The quick brown fox jumps over the lazy dog",
            "doc_id": "doc1",
            "doc_title": "Document 1",
            "chunk_index": 0
        },
        {
            "text": "Python programming language is great for data science",
            "doc_id": "doc1",
            "doc_title": "Document 1",
            "chunk_index": 1
        },
        {
            "text": "Machine learning models require large datasets",
            "doc_id": "doc2",
            "doc_title": "Document 2",
            "chunk_index": 0
        },
        {
            "text": "Deep learning uses neural networks with many layers",
            "doc_id": "doc2",
            "doc_title": "Document 2",
            "chunk_index": 1
        },
        {
            "text": "The lazy cat sleeps all day long",
            "doc_id": "doc3",
            "doc_title": "Document 3",
            "chunk_index": 0
        }
    ]


@pytest.fixture
def bm25_index(tmp_path):
    """BM25 index instance with temporary cache directory."""
    cache_dir = str(tmp_path / "bm25_cache")
    index = BM25Index(cache_dir=cache_dir)
    yield index
    # Cleanup
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)


class TestBM25Index:
    """Test suite for BM25Index."""

    def test_initialization(self, bm25_index):
        """Test BM25Index initialization."""
        assert bm25_index.index is None
        assert len(bm25_index.doc_ids) == 0
        assert len(bm25_index.chunks) == 0
        assert os.path.exists(bm25_index.cache_dir)

    def test_build_index(self, bm25_index, sample_chunks):
        """Test building BM25 index."""
        bm25_index.build_index(sample_chunks)

        assert bm25_index.index is not None
        assert len(bm25_index.doc_ids) == len(sample_chunks)
        assert len(bm25_index.chunks) == len(sample_chunks)
        assert bm25_index.doc_ids == ["doc1", "doc1", "doc2", "doc2", "doc3"]

    def test_build_index_empty_chunks(self, bm25_index):
        """Test building index with empty chunks."""
        bm25_index.build_index([])

        assert bm25_index.index is None
        assert len(bm25_index.chunks) == 0

    def test_search_basic(self, bm25_index, sample_chunks):
        """Test basic BM25 search."""
        bm25_index.build_index(sample_chunks)

        # Search for "python"
        results = bm25_index.search("python", top_k=3)

        assert len(results) > 0
        # Check that the Python chunk is in results
        assert any("Python programming" in r["chunk"]["text"] for r in results)
        # Check structure
        assert "chunk_index" in results[0]
        assert "score" in results[0]
        assert "doc_id" in results[0]
        assert "chunk" in results[0]

    def test_search_multiple_terms(self, bm25_index, sample_chunks):
        """Test search with multiple terms."""
        bm25_index.build_index(sample_chunks)

        # Search for "lazy dog"
        results = bm25_index.search("lazy dog", top_k=5)

        assert len(results) > 0
        # The "quick brown fox" chunk should rank high
        top_result = results[0]
        assert "lazy dog" in top_result["chunk"]["text"] or "lazy" in top_result["chunk"]["text"]

    def test_search_no_results(self, bm25_index, sample_chunks):
        """Test search with no matching results."""
        bm25_index.build_index(sample_chunks)

        # Search for term that doesn't exist
        results = bm25_index.search("zzzznonexistent", top_k=5)

        # Should return empty or very low scores
        assert len(results) == 0 or all(r["score"] < 0.1 for r in results)

    def test_search_with_doc_filter(self, bm25_index, sample_chunks):
        """Test search filtered by document IDs."""
        bm25_index.build_index(sample_chunks)

        # Search only in doc1
        results = bm25_index.search("python", top_k=5, doc_ids=["doc1"])

        assert len(results) > 0
        # All results should be from doc1
        assert all(r["doc_id"] == "doc1" for r in results)

    def test_search_with_doc_filter_no_match(self, bm25_index, sample_chunks):
        """Test search with doc filter that excludes all matches."""
        bm25_index.build_index(sample_chunks)

        # Search for "python" but only in doc2 (which doesn't have it)
        results = bm25_index.search("python", top_k=5, doc_ids=["doc2"])

        # Should have no results or very low scores
        assert len(results) == 0 or all(r["score"] < 0.1 for r in results)

    def test_search_empty_query(self, bm25_index, sample_chunks):
        """Test search with empty query."""
        bm25_index.build_index(sample_chunks)

        results = bm25_index.search("", top_k=5)

        # Empty query should return no meaningful results
        assert len(results) == 0

    def test_search_before_build(self, bm25_index):
        """Test search before building index."""
        results = bm25_index.search("test", top_k=5)

        assert len(results) == 0

    def test_top_k_limit(self, bm25_index, sample_chunks):
        """Test that top_k limit is respected."""
        bm25_index.build_index(sample_chunks)

        results = bm25_index.search("the", top_k=2)

        # Should return at most 2 results
        assert len(results) <= 2

    def test_cache_save_and_load(self, bm25_index, sample_chunks):
        """Test saving and loading BM25 index cache."""
        # Build index
        bm25_index.build_index(sample_chunks)

        # Get a search result before cache
        results_before = bm25_index.search("python", top_k=3)

        # Create new index instance with same cache dir
        new_index = BM25Index(cache_dir=bm25_index.cache_dir)

        # Load cache
        loaded = new_index.load_cache()

        assert loaded is True
        assert new_index.index is not None
        assert len(new_index.chunks) == len(sample_chunks)

        # Search should give same results
        results_after = new_index.search("python", top_k=3)

        assert len(results_after) == len(results_before)
        assert results_after[0]["doc_id"] == results_before[0]["doc_id"]

    def test_cache_load_nonexistent(self, bm25_index):
        """Test loading cache when none exists."""
        loaded = bm25_index.load_cache()

        assert loaded is False
        assert bm25_index.index is None

    def test_clear_cache(self, bm25_index, sample_chunks):
        """Test clearing BM25 cache."""
        # Build and save
        bm25_index.build_index(sample_chunks)

        # Clear cache
        bm25_index.clear_cache()

        # Cache file should not exist
        cache_file = os.path.join(bm25_index.cache_dir, "bm25_index.pkl")
        assert not os.path.exists(cache_file)

    def test_case_insensitivity(self, bm25_index, sample_chunks):
        """Test that search is case-insensitive."""
        bm25_index.build_index(sample_chunks)

        results_lower = bm25_index.search("python", top_k=3)
        results_upper = bm25_index.search("PYTHON", top_k=3)
        results_mixed = bm25_index.search("PyThOn", top_k=3)

        # Should all return the same top result
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0
        assert results_lower[0]["doc_id"] == results_upper[0]["doc_id"]
        assert results_lower[0]["doc_id"] == results_mixed[0]["doc_id"]

    def test_score_ordering(self, bm25_index, sample_chunks):
        """Test that results are ordered by score (descending)."""
        bm25_index.build_index(sample_chunks)

        results = bm25_index.search("learning", top_k=5)

        # Scores should be in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rebuild_index(self, bm25_index, sample_chunks):
        """Test rebuilding index with new chunks."""
        # Build initial index
        bm25_index.build_index(sample_chunks[:3])
        assert len(bm25_index.chunks) == 3

        # Rebuild with all chunks
        bm25_index.build_index(sample_chunks)
        assert len(bm25_index.chunks) == 5

        # Search should work with new chunks
        results = bm25_index.search("lazy cat", top_k=5)
        assert len(results) > 0
        assert any("cat" in r["chunk"]["text"] for r in results)
