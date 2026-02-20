"""Tests for InteractionLogger and FeedbackStore."""

import json
import pytest

from src.interaction_logger import InteractionLogger
from src.feedback_store import FeedbackStore


class TestInteractionLogger:
    """Test InteractionLogger JSONL operations."""

    def test_creates_file(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        logger.log_interaction(
            chat_id="c1", question="Q?", answer="A.",
            sources=[], latency_ms=100, doc_ids=["d1"], config={},
        )
        assert logger.file_path.exists()

    def test_appends_entries(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        for i in range(3):
            logger.log_interaction(
                chat_id="c1", question=f"Q{i}?", answer=f"A{i}.",
                sources=[], latency_ms=100, doc_ids=[], config={},
            )
        entries = logger.get_interactions(limit=10)
        assert len(entries) == 3

    def test_truncates_sources(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        long_text = "x" * 500
        logger.log_interaction(
            chat_id="c1", question="Q?", answer="A.",
            sources=[{"chunk_text": long_text, "doc_id": "d1", "doc_title": "T", "score": 0.9}],
            latency_ms=100, doc_ids=[], config={},
        )
        entries = logger.get_interactions()
        assert len(entries[0]["sources"][0]["chunk_text"]) <= 200

    def test_get_with_limit(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        for i in range(5):
            logger.log_interaction(
                chat_id="c1", question=f"Q{i}?", answer=f"A{i}.",
                sources=[], latency_ms=100, doc_ids=[], config={},
            )
        entries = logger.get_interactions(limit=2)
        assert len(entries) == 2

    def test_filter_by_chat_id(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        logger.log_interaction(
            chat_id="c1", question="Q1?", answer="A1.",
            sources=[], latency_ms=100, doc_ids=[], config={},
        )
        logger.log_interaction(
            chat_id="c2", question="Q2?", answer="A2.",
            sources=[], latency_ms=100, doc_ids=[], config={},
        )
        entries = logger.get_interactions(chat_id="c1")
        assert len(entries) == 1
        assert entries[0]["chat_id"] == "c1"

    def test_empty_file(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        assert logger.get_interactions() == []

    def test_malformed_lines_skipped(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        # Write a valid entry then a malformed one
        logger.log_interaction(
            chat_id="c1", question="Q?", answer="A.",
            sources=[], latency_ms=100, doc_ids=[], config={},
        )
        with open(logger.file_path, "a") as f:
            f.write("not json\n")
        entries = logger.get_interactions()
        assert len(entries) == 1

    def test_message_id(self, tmp_path):
        logger = InteractionLogger(data_dir=str(tmp_path))
        logger.log_interaction(
            chat_id="c1", question="Q?", answer="A.",
            sources=[], latency_ms=100, doc_ids=[], config={},
            message_id="m1",
        )
        entries = logger.get_interactions()
        assert entries[0]["message_id"] == "m1"


class TestFeedbackStore:
    """Test FeedbackStore JSONL operations."""

    def test_creates_file(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        store.add_feedback(
            message_id="m1", chat_id="c1", feedback="up",
            question="Q?", answer="A.", doc_ids=["d1"],
        )
        assert store.file_path.exists()

    def test_appends_entries(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        store.add_feedback(
            message_id="m1", chat_id="c1", feedback="up",
            question="Q?", answer="A.", doc_ids=[],
        )
        store.add_feedback(
            message_id="m2", chat_id="c1", feedback="down",
            question="Q2?", answer="A2.", doc_ids=[],
        )
        entries = store.get_feedback()
        assert len(entries) == 2

    def test_get_with_limit(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        for i in range(5):
            store.add_feedback(
                message_id=f"m{i}", chat_id="c1", feedback="up",
                question=f"Q{i}?", answer=f"A{i}.", doc_ids=[],
            )
        entries = store.get_feedback(limit=2)
        assert len(entries) == 2

    def test_filter_by_chat_id(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        store.add_feedback(
            message_id="m1", chat_id="c1", feedback="up",
            question="Q?", answer="A.", doc_ids=[],
        )
        store.add_feedback(
            message_id="m2", chat_id="c2", feedback="up",
            question="Q?", answer="A.", doc_ids=[],
        )
        entries = store.get_feedback(chat_id="c1")
        assert len(entries) == 1

    def test_filter_by_feedback_type(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        store.add_feedback(
            message_id="m1", chat_id="c1", feedback="up",
            question="Q?", answer="A.", doc_ids=[],
        )
        store.add_feedback(
            message_id="m2", chat_id="c1", feedback="down",
            question="Q?", answer="A.", doc_ids=[],
        )
        up = store.get_feedback(feedback_filter="up")
        down = store.get_feedback(feedback_filter="down")
        assert len(up) == 1
        assert len(down) == 1

    def test_dual_filter(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        store.add_feedback(message_id="m1", chat_id="c1", feedback="up", question="Q?", answer="A.", doc_ids=[])
        store.add_feedback(message_id="m2", chat_id="c1", feedback="down", question="Q?", answer="A.", doc_ids=[])
        store.add_feedback(message_id="m3", chat_id="c2", feedback="up", question="Q?", answer="A.", doc_ids=[])
        entries = store.get_feedback(chat_id="c1", feedback_filter="up")
        assert len(entries) == 1
        assert entries[0]["message_id"] == "m1"

    def test_empty(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        assert store.get_feedback() == []

    def test_sources_stored(self, tmp_path):
        store = FeedbackStore(data_dir=str(tmp_path))
        sources = [{"doc_id": "d1", "score": 0.9}]
        store.add_feedback(
            message_id="m1", chat_id="c1", feedback="up",
            question="Q?", answer="A.", doc_ids=[], sources=sources,
        )
        entries = store.get_feedback()
        assert entries[0]["sources"] == sources
