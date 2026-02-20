"""Tests for data models and DocumentStore."""

import json
import os
import threading
import pytest

from src.models import DocumentMetadata, DocumentChunk, DocumentStore, Chat, ChatMessage


class TestDocumentMetadata:
    """Test DocumentMetadata dataclass."""

    def _sample(self, **overrides):
        defaults = dict(
            doc_id="d1", title="T", filename="f.pdf", file_path="/tmp/f.pdf",
            format="pdf", upload_date="2025-01-01", file_size_mb=1.5,
        )
        defaults.update(overrides)
        return DocumentMetadata(**defaults)

    def test_to_dict_roundtrip(self):
        doc = self._sample(chunk_count=5, total_pages=10, metadata={"k": "v"})
        d = doc.to_dict()
        restored = DocumentMetadata.from_dict(d)
        assert restored.doc_id == doc.doc_id
        assert restored.chunk_count == 5
        assert restored.total_pages == 10
        assert restored.metadata == {"k": "v"}

    def test_default_fields(self):
        doc = self._sample()
        assert doc.chunk_count == 0
        assert doc.total_pages is None
        assert doc.metadata == {}

    def test_from_dict_with_all_fields(self):
        data = {
            "doc_id": "x", "title": "X", "filename": "x.pdf",
            "file_path": "/tmp/x.pdf", "format": "pdf",
            "upload_date": "2025-01-01", "file_size_mb": 2.0,
            "chunk_count": 3, "total_pages": 5, "metadata": {"a": 1},
        }
        doc = DocumentMetadata.from_dict(data)
        assert doc.doc_id == "x"
        assert doc.chunk_count == 3


class TestDocumentChunk:
    """Test DocumentChunk dataclass."""

    def _sample(self, **overrides):
        defaults = dict(
            text="chunk text", doc_id="d1", doc_title="Doc",
            chunk_index=0,
        )
        defaults.update(overrides)
        return DocumentChunk(**defaults)

    def test_build_enriched_text_basic(self):
        chunk = self._sample()
        result = chunk.build_enriched_text()
        assert result.startswith("[Document: Doc]")
        assert "chunk text" in result
        assert chunk.enriched_text == result

    def test_build_enriched_text_with_page(self):
        chunk = self._sample(page_num=3)
        result = chunk.build_enriched_text()
        assert "Page: 3" in result

    def test_build_enriched_text_with_section(self):
        chunk = self._sample(section_title="Intro")
        result = chunk.build_enriched_text()
        assert "Section: Intro" in result

    def test_build_enriched_text_with_page_and_section(self):
        chunk = self._sample(page_num=2, section_title="Ch1")
        result = chunk.build_enriched_text()
        assert "Page: 2" in result
        assert "Section: Ch1" in result

    def test_to_payload(self):
        chunk = self._sample(page_num=1, section_title="S", metadata={"k": "v"})
        chunk.build_enriched_text()
        payload = chunk.to_payload()
        assert payload["text"] == "chunk text"
        assert payload["doc_id"] == "d1"
        assert payload["doc_title"] == "Doc"
        assert payload["chunk_index"] == 0
        assert payload["page_num"] == 1
        assert payload["section_title"] == "S"
        assert "enriched_text" in payload
        assert payload["metadata"] == {"k": "v"}


class TestDocumentStore:
    """Test DocumentStore JSON-based storage."""

    def _make_doc(self, doc_id="d1", filename="test.pdf"):
        return DocumentMetadata(
            doc_id=doc_id, title="Test", filename=filename,
            file_path=f"/tmp/{filename}", format="pdf",
            upload_date="2025-01-01", file_size_mb=1.0,
        )

    def test_init_creates_dir_and_file(self, tmp_path):
        data_dir = str(tmp_path / "newdir")
        store = DocumentStore(data_dir=data_dir)
        assert os.path.isdir(data_dir)
        assert os.path.isfile(store.metadata_file)

    def test_save_and_get(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        doc = self._make_doc()
        store.save_document(doc)
        result = store.get_document("d1")
        assert result is not None
        assert result.doc_id == "d1"

    def test_get_nonexistent(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        assert store.get_document("missing") is None

    def test_delete(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        store.save_document(self._make_doc())
        assert store.delete_document("d1") is True
        assert store.get_document("d1") is None

    def test_delete_nonexistent(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        assert store.delete_document("missing") is False

    def test_list_documents(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        store.save_document(self._make_doc("d1", "a.pdf"))
        store.save_document(self._make_doc("d2", "b.pdf"))
        docs = store.list_documents()
        assert len(docs) == 2
        ids = {d.doc_id for d in docs}
        assert ids == {"d1", "d2"}

    def test_find_by_filename(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        store.save_document(self._make_doc("d1", "target.pdf"))
        store.save_document(self._make_doc("d2", "other.pdf"))
        found = store.find_by_filename("target.pdf")
        assert found is not None
        assert found.doc_id == "d1"
        assert store.find_by_filename("missing.pdf") is None

    def test_thread_safety(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        errors = []

        def writer(i):
            try:
                store.save_document(self._make_doc(f"d{i}", f"f{i}.pdf"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(store.list_documents()) == 10

    def test_load_all_corrupted_file(self, tmp_path):
        store = DocumentStore(data_dir=str(tmp_path))
        with open(store.metadata_file, "w") as f:
            f.write("not json")
        assert store.load_all() == {}


class TestChat:
    """Test Chat dataclass."""

    def test_roundtrip(self):
        chat = Chat(
            id="c1", name="Test", doc_ids=["d1"],
            created_at="2025-01-01", updated_at="2025-01-01",
        )
        d = chat.to_dict()
        restored = Chat.from_dict(d)
        assert restored.id == "c1"
        assert restored.doc_ids == ["d1"]

    def test_from_dict_filters_unknown_fields(self):
        data = {
            "id": "c1", "name": "T", "doc_ids": [],
            "created_at": "x", "updated_at": "x",
            "unknown_field": "should be ignored",
        }
        chat = Chat.from_dict(data)
        assert chat.id == "c1"
        assert not hasattr(chat, "unknown_field")

    def test_default_fields(self):
        chat = Chat(id="c1", name="T", doc_ids=[], created_at="x", updated_at="x")
        assert chat.message_count == 0
        assert chat.gemini_chat_history == []
        assert chat.auto_route is False
        assert chat.user_id == ""


class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_roundtrip(self):
        msg = ChatMessage(
            id="m1", chat_id="c1", role="user",
            content="Hello", timestamp="2025-01-01",
        )
        d = msg.to_dict()
        restored = ChatMessage.from_dict(d)
        assert restored.id == "m1"
        assert restored.content == "Hello"
        assert restored.sources is None

    def test_with_sources(self):
        msg = ChatMessage(
            id="m1", chat_id="c1", role="assistant",
            content="Answer", timestamp="2025-01-01",
            sources=[{"doc_id": "d1", "score": 0.9}],
        )
        d = msg.to_dict()
        assert d["sources"] == [{"doc_id": "d1", "score": 0.9}]
