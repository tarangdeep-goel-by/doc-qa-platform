"""Tests for BM25-based document routing."""

import pytest
from unittest.mock import MagicMock, PropertyMock
import numpy as np

from src.doc_router import route_query


class TestRouteQuery:
    """Test route_query() function."""

    def _make_index(self, chunks=None, doc_ids=None, scores=None):
        """Create a mock BM25Index."""
        index = MagicMock()
        index.chunks = chunks or []
        index.doc_ids = doc_ids or []

        if scores is not None:
            mock_bm25 = MagicMock()
            mock_bm25.get_scores.return_value = scores
            index.index = mock_bm25
        else:
            index.index = None

        return index

    def test_empty_index(self):
        bm25 = self._make_index(chunks=[], doc_ids=[])
        result = route_query("test question", bm25)
        assert result == []

    def test_empty_chunks(self):
        bm25 = self._make_index(chunks=[], doc_ids=["d1"])
        bm25.index = MagicMock()
        result = route_query("test question", bm25)
        assert result == []

    def test_single_doc_above_threshold(self):
        chunks = [{"text": "chunk1"}, {"text": "chunk2"}]
        doc_ids = ["d1", "d1"]
        scores = np.array([5.0, 3.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        result = route_query("test question", bm25)
        assert result == ["d1"]

    def test_multiple_docs_threshold_filter(self):
        chunks = [{"text": "c1"}, {"text": "c2"}, {"text": "c3"}]
        doc_ids = ["d1", "d2", "d3"]
        # d1=10.0, d2=5.0, d3=1.0
        # With min_score_ratio=0.45, threshold=4.5 → d1 and d2 pass
        scores = np.array([10.0, 5.0, 1.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        result = route_query("test question", bm25, min_score_ratio=0.45)
        assert "d1" in result
        assert "d2" in result
        assert "d3" not in result

    def test_max_docs_cap(self):
        chunks = [{"text": f"c{i}"} for i in range(5)]
        doc_ids = [f"d{i}" for i in range(5)]
        scores = np.array([10.0, 9.0, 8.0, 7.0, 6.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        result = route_query("test question", bm25, max_docs=2)
        assert len(result) <= 2

    def test_no_scores(self):
        chunks = [{"text": "c1"}]
        doc_ids = ["d1"]
        scores = np.array([0.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        result = route_query("test question", bm25)
        assert result == []

    def test_score_aggregation_across_chunks(self):
        # Two chunks for d1, one for d2
        chunks = [{"text": "c1"}, {"text": "c2"}, {"text": "c3"}]
        doc_ids = ["d1", "d1", "d2"]
        # d1 total = 3+4 = 7, d2 total = 6
        scores = np.array([3.0, 4.0, 6.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        result = route_query("test question", bm25, min_score_ratio=0.45)
        assert "d1" in result
        # d2 has 6/7 = 0.857 > 0.45 threshold
        assert "d2" in result

    def test_empty_tokens(self):
        """Query with only stop words should return empty."""
        chunks = [{"text": "c1"}]
        doc_ids = ["d1"]
        scores = np.array([5.0])
        bm25 = self._make_index(chunks=chunks, doc_ids=doc_ids, scores=scores)

        # "the a an" are all stop words → empty token list
        result = route_query("the a an", bm25)
        assert result == []
