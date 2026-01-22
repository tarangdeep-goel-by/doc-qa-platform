"""Tests for hybrid search (vector + BM25)."""

import pytest
import numpy as np
from src.vector_store import VectorStore
from src.embedder import Embedder


@pytest.fixture
def embedder():
    """Embedder instance for testing."""
    return Embedder()


@pytest.fixture
def vector_store():
    """VectorStore instance for testing."""
    # Use test collection name
    store = VectorStore(collection_name="test_hybrid_search")
    yield store
    # Cleanup - delete test collection
    try:
        store.client.delete_collection("test_hybrid_search")
    except:
        pass


@pytest.fixture
def sample_documents(embedder, vector_store):
    """Add sample documents to vector store."""
    chunks = [
        {
            "text": "Python is a high-level programming language. It is widely used for data science.",
            "doc_id": "doc1",
            "doc_title": "Python Guide",
            "chunk_index": 0,
            "metadata": {}
        },
        {
            "text": "Machine learning models require large datasets for training. Python has libraries like scikit-learn.",
            "doc_id": "doc1",
            "doc_title": "Python Guide",
            "chunk_index": 1,
            "metadata": {}
        },
        {
            "text": "JavaScript is a programming language used for web development. It runs in browsers.",
            "doc_id": "doc2",
            "doc_title": "JavaScript Guide",
            "chunk_index": 0,
            "metadata": {}
        },
        {
            "text": "Deep learning uses neural networks with multiple layers. TensorFlow is popular.",
            "doc_id": "doc3",
            "doc_title": "Deep Learning",
            "chunk_index": 0,
            "metadata": {}
        }
    ]

    # Embed and store
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_texts(texts)
    vector_store.add_document_chunks(chunks, embeddings)

    return chunks


class TestHybridSearch:
    """Test suite for hybrid search functionality."""

    def test_hybrid_search_basic(self, vector_store, embedder, sample_documents):
        """Test basic hybrid search."""
        query = "Python programming"
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.5
        )

        assert len(results) > 0
        assert len(results) <= 3
        # Check structure
        assert "id" in results[0]
        assert "score" in results[0]
        assert "payload" in results[0]

    def test_hybrid_search_vs_pure_vector(self, vector_store, embedder, sample_documents):
        """Test that hybrid search can find different results than pure vector."""
        query = "Python scikit-learn"
        query_vector = embedder.embed_text(query)

        # Pure vector search
        vector_results = vector_store.search(
            query_vector=query_vector,
            top_k=3
        )

        # Hybrid search
        hybrid_results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.5
        )

        # Both should return results
        assert len(vector_results) > 0
        assert len(hybrid_results) > 0

        # Results might be different due to BM25 contribution
        # At minimum, check that hybrid search works
        assert all("score" in r for r in hybrid_results)

    def test_hybrid_search_alpha_variations(self, vector_store, embedder, sample_documents):
        """Test hybrid search with different alpha values."""
        query = "machine learning"
        query_vector = embedder.embed_text(query)

        # All vector (alpha=1.0)
        all_vector = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=1.0
        )

        # All BM25 (alpha=0.0)
        all_bm25 = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.0
        )

        # Balanced (alpha=0.5)
        balanced = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.5
        )

        # All should return results
        assert len(all_vector) > 0
        assert len(all_bm25) > 0
        assert len(balanced) > 0

    def test_hybrid_search_with_doc_filter(self, vector_store, embedder, sample_documents):
        """Test hybrid search filtered by document IDs."""
        query = "programming"
        query_vector = embedder.embed_text(query)

        # Search only in doc1
        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=5,
            doc_ids=["doc1"],
            alpha=0.5
        )

        assert len(results) > 0
        # All results should be from doc1
        assert all(r["payload"]["doc_id"] == "doc1" for r in results)

    def test_hybrid_search_keyword_matching(self, vector_store, embedder, sample_documents):
        """Test that hybrid search finds exact keyword matches."""
        # Search for specific term "scikit-learn"
        query = "scikit-learn"
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.3  # Favor BM25 for keyword matching
        )

        # Should find the chunk with "scikit-learn"
        assert len(results) > 0
        assert any("scikit-learn" in r["payload"]["text"] for r in results)

    def test_rebuild_bm25_index(self, vector_store, embedder, sample_documents):
        """Test rebuilding BM25 index."""
        # Rebuild index
        vector_store.rebuild_bm25_index()

        # BM25 index should be populated
        assert vector_store.bm25_index.index is not None
        assert len(vector_store.bm25_index.chunks) > 0

        # Search should still work
        query = "Python"
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.5
        )

        assert len(results) > 0

    def test_hybrid_search_after_delete(self, vector_store, embedder, sample_documents):
        """Test hybrid search after deleting a document."""
        # Delete doc2
        vector_store.delete_document("doc2")

        # Hybrid search should work without doc2
        query = "programming"
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=5,
            alpha=0.5
        )

        # Should not include doc2
        assert all(r["payload"]["doc_id"] != "doc2" for r in results)

    def test_normalize_scores(self, vector_store):
        """Test score normalization helper."""
        scores = [0.5, 0.8, 0.3, 0.9, 0.1]

        normalized = vector_store._normalize_scores(scores)

        # Should be in 0-1 range
        assert all(0 <= s <= 1 for s in normalized)
        # Max should be 1.0
        assert max(normalized) == 1.0
        # Min should be 0.0
        assert min(normalized) == 0.0

    def test_normalize_scores_all_same(self, vector_store):
        """Test normalizing scores when all are the same."""
        scores = [0.5, 0.5, 0.5]

        normalized = vector_store._normalize_scores(scores)

        # All should be 1.0 when identical
        assert all(s == 1.0 for s in normalized)

    def test_normalize_scores_empty(self, vector_store):
        """Test normalizing empty score list."""
        scores = []

        normalized = vector_store._normalize_scores(scores)

        assert normalized == []

    def test_hybrid_search_score_ordering(self, vector_store, embedder, sample_documents):
        """Test that hybrid search results are ordered by score."""
        query = "Python machine learning"
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=4,
            alpha=0.5
        )

        # Scores should be in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_hybrid_search_empty_query(self, vector_store, embedder, sample_documents):
        """Test hybrid search with empty query."""
        query = ""
        query_vector = embedder.embed_text(query)

        results = vector_store.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=3,
            alpha=0.5
        )

        # Should handle gracefully (might return results or empty)
        assert isinstance(results, list)

    def test_bm25_index_cache_persistence(self, vector_store, embedder, sample_documents):
        """Test that BM25 index cache persists."""
        # Rebuild to create cache
        vector_store.rebuild_bm25_index()

        # Check cache was saved
        import os
        cache_file = os.path.join(vector_store.bm25_index.cache_dir, "bm25_index.pkl")
        assert os.path.exists(cache_file)

        # Create new vector store and load cache
        new_store = VectorStore(collection_name="test_hybrid_search")
        loaded = new_store.bm25_index.load_cache()

        # Should load successfully
        assert loaded is True
        assert new_store.bm25_index.index is not None

        # Cleanup
        try:
            new_store.client.delete_collection("test_hybrid_search")
        except:
            pass
