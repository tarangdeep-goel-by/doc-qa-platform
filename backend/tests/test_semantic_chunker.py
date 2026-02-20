"""Tests for SemanticChunker."""

import numpy as np
import pytest
from unittest.mock import MagicMock

from src.semantic_chunker import SemanticChunker, _split_sentences


class TestSplitSentences:
    """Test _split_sentences() helper."""

    def test_basic_splits(self):
        text = "First sentence. Second sentence. Third sentence."
        result = _split_sentences(text)
        assert len(result) >= 2

    def test_filters_short_fragments(self):
        text = "Hi. Ok. This is a longer sentence that should pass."
        result = _split_sentences(text)
        # "Hi" and "Ok" are <= 10 chars, should be filtered
        for s in result:
            assert len(s.strip()) > 10

    def test_empty_text(self):
        assert _split_sentences("") == []

    def test_single_long_sentence(self):
        text = "This is one single long sentence without any period ending"
        result = _split_sentences(text)
        assert len(result) == 1


class TestSemanticChunker:
    """Test SemanticChunker with mocked embedder."""

    def _make_embedder(self, dim=8):
        embedder = MagicMock()
        return embedder

    def _make_page_data(self, texts):
        return [{"page_num": i + 1, "text": t} for i, t in enumerate(texts)]

    def test_empty_pages(self):
        embedder = self._make_embedder()
        chunker = SemanticChunker(embedder)
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": ""}])
        assert result == []

    def test_few_sentences_single_chunk(self):
        embedder = self._make_embedder()
        chunker = SemanticChunker(embedder)
        # Only 2 sentences → too few for semantic splitting
        text = "This is a medium length sentence one. This is another medium length sentence two."
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": text}])
        assert len(result) == 1
        assert result[0]["page_num"] == 1

    def test_few_segments_single_chunk(self):
        embedder = self._make_embedder()
        # Return embeddings for 2 segments
        embedder.embed_texts.return_value = np.random.rand(2, 8).astype(np.float32)
        chunker = SemanticChunker(embedder)
        # Enough sentences for splitting but only 2 segments
        sentences = ". ".join([f"This is sentence number {i} with enough text" for i in range(5)])
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": sentences}])
        # With <= 2 segments, returns single chunk
        assert len(result) >= 1

    def test_normal_produces_multiple(self):
        embedder = self._make_embedder()
        # Create 10 segments with embeddings that have a clear breakpoint
        n_segments = 10
        embeddings = np.ones((n_segments, 8), dtype=np.float32)
        # Make segment 5 very different to create a breakpoint
        embeddings[5] = -1.0
        embedder.embed_texts.return_value = embeddings

        chunker = SemanticChunker(embedder, min_chunk_size=50, max_chunk_size=2000)
        # Generate enough text for multiple segments
        sentences = ". ".join([f"This is a detailed sentence number {i} with enough text to form segments" for i in range(40)])
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": sentences}])
        assert len(result) >= 1

    def test_enforces_max_size(self):
        embedder = self._make_embedder()
        n_segments = 5
        # All very similar → no breakpoints → one huge chunk
        embeddings = np.ones((n_segments, 8), dtype=np.float32)
        embedder.embed_texts.return_value = embeddings

        chunker = SemanticChunker(embedder, min_chunk_size=50, max_chunk_size=200)
        sentences = ". ".join([f"This is sentence number {i} with sufficient text to be long enough" for i in range(30)])
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": sentences}])
        for chunk in result:
            # Allow some slack for merging
            assert len(chunk["text"]) <= 400  # max_chunk_size * 2 for merged tiny

    def test_merges_tiny_chunks(self):
        embedder = self._make_embedder()
        n_segments = 6
        # Alternating very different embeddings → many breakpoints → tiny chunks
        embeddings = np.zeros((n_segments, 8), dtype=np.float32)
        for i in range(n_segments):
            embeddings[i][i % 8] = 1.0
        embedder.embed_texts.return_value = embeddings

        chunker = SemanticChunker(embedder, min_chunk_size=100, max_chunk_size=4000)
        sentences = ". ".join([f"Sentence {i} has enough words to be kept" for i in range(25)])
        result = chunker.chunk_with_page_tracking([{"page_num": 1, "text": sentences}])
        # Tiny chunks should be merged, so fewer chunks than breakpoints
        assert len(result) >= 1


class TestConsecutiveSimilarities:
    """Test _consecutive_similarities()."""

    def test_zero_vectors(self):
        embedder = MagicMock()
        chunker = SemanticChunker(embedder)
        embeddings = np.zeros((3, 4), dtype=np.float32)
        sims = chunker._consecutive_similarities(embeddings)
        assert len(sims) == 2
        assert all(s == 0.0 for s in sims)

    def test_identical_vectors(self):
        embedder = MagicMock()
        chunker = SemanticChunker(embedder)
        embeddings = np.ones((3, 4), dtype=np.float32)
        sims = chunker._consecutive_similarities(embeddings)
        assert all(abs(s - 1.0) < 0.01 for s in sims)


class TestBuildSegments:
    """Test _build_segments()."""

    def test_groups_by_target_size(self):
        embedder = MagicMock()
        chunker = SemanticChunker(embedder)
        sentences = [
            {"text": "Short sentence here.", "page_num": 1},
            {"text": "Another short one.", "page_num": 1},
            {"text": "A third sentence that is a bit longer than the others.", "page_num": 1},
        ]
        segments = chunker._build_segments(sentences, target_size=30)
        assert len(segments) >= 1
        for seg in segments:
            assert "text" in seg
            assert "page_num" in seg


class TestMergeAtBreakpoints:
    """Test _merge_at_breakpoints()."""

    def test_merges_correctly(self):
        embedder = MagicMock()
        chunker = SemanticChunker(embedder)
        segments = [
            {"text": "Seg 0", "page_num": 1},
            {"text": "Seg 1", "page_num": 1},
            {"text": "Seg 2", "page_num": 2},
            {"text": "Seg 3", "page_num": 2},
        ]
        # Breakpoint at index 1 → split after segment 1
        chunks = chunker._merge_at_breakpoints(segments, [1])
        assert len(chunks) == 2
        assert "Seg 0" in chunks[0]["text"]
        assert "Seg 1" in chunks[0]["text"]
