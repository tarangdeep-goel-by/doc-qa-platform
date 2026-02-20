"""Tests for ChatManager filesystem operations."""

import json
import pytest

from src.chat_manager import ChatManager
from src.models import Chat, ChatMessage


class TestCreateChat:
    """Test create_chat()."""

    def test_basic_create(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test Chat", doc_ids=["d1", "d2"])
        assert chat.name == "Test Chat"
        assert chat.doc_ids == ["d1", "d2"]
        assert chat.message_count == 0
        assert chat.id  # UUID assigned

    def test_directory_creation(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test", doc_ids=[])
        chat_dir = tmp_path / "chats" / chat.id
        assert chat_dir.exists()
        assert (chat_dir / "metadata.json").exists()
        assert (chat_dir / "messages.json").exists()

    def test_auto_route_flag(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Auto", doc_ids=[], auto_route=True)
        assert chat.auto_route is True

    def test_user_id(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="T", doc_ids=[], user_id="u1")
        assert chat.user_id == "u1"


class TestGetChat:
    """Test get_chat()."""

    def test_returns_chat_and_messages(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        created = mgr.create_chat(name="Test", doc_ids=["d1"])
        chat, messages = mgr.get_chat(created.id)
        assert chat is not None
        assert chat.name == "Test"
        assert messages == []

    def test_nonexistent(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat, messages = mgr.get_chat("nonexistent-id")
        assert chat is None
        assert messages == []

    def test_corrupted_metadata(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        created = mgr.create_chat(name="Test", doc_ids=[])
        # Corrupt the metadata file
        meta_file = tmp_path / "chats" / created.id / "metadata.json"
        meta_file.write_text("not json")
        chat, messages = mgr.get_chat(created.id)
        assert chat is None

    def test_corrupted_messages(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        created = mgr.create_chat(name="Test", doc_ids=[])
        # Corrupt messages file
        msg_file = tmp_path / "chats" / created.id / "messages.json"
        msg_file.write_text("not json")
        chat, messages = mgr.get_chat(created.id)
        assert chat is not None
        assert messages == []


class TestListChats:
    """Test list_chats()."""

    def test_sorted_by_updated_at(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        c1 = mgr.create_chat(name="First", doc_ids=[])
        c2 = mgr.create_chat(name="Second", doc_ids=[])
        chats = mgr.list_chats()
        assert len(chats) == 2
        # Most recently created should be first
        assert chats[0].updated_at >= chats[1].updated_at

    def test_empty(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        assert mgr.list_chats() == []


class TestAddMessage:
    """Test add_message()."""

    def test_increments_count(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test", doc_ids=[])
        msg = ChatMessage(
            id="m1", chat_id=chat.id, role="user",
            content="Hello", timestamp="2025-01-01",
        )
        assert mgr.add_message(chat.id, msg) is True
        updated_chat, messages = mgr.get_chat(chat.id)
        assert updated_chat.message_count == 1
        assert len(messages) == 1
        assert messages[0].content == "Hello"

    def test_nonexistent_chat(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        msg = ChatMessage(
            id="m1", chat_id="missing", role="user",
            content="Hello", timestamp="2025-01-01",
        )
        assert mgr.add_message("missing", msg) is False


class TestDeleteChat:
    """Test delete_chat()."""

    def test_removes_dir(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test", doc_ids=[])
        chat_dir = tmp_path / "chats" / chat.id
        assert chat_dir.exists()
        assert mgr.delete_chat(chat.id) is True
        assert not chat_dir.exists()

    def test_nonexistent(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        assert mgr.delete_chat("missing") is False


class TestRenameChat:
    """Test rename_chat()."""

    def test_name_changes(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Old", doc_ids=[])
        assert mgr.rename_chat(chat.id, "New Name") is True
        updated, _ = mgr.get_chat(chat.id)
        assert updated.name == "New Name"

    def test_nonexistent(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        assert mgr.rename_chat("missing", "New") is False


class TestUpdateGeminiHistory:
    """Test update_gemini_history()."""

    def test_updates_history(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test", doc_ids=[])
        history = [{"question": "Q1", "answer": "A1"}]
        assert mgr.update_gemini_history(chat.id, history) is True
        updated, _ = mgr.get_chat(chat.id)
        assert updated.gemini_chat_history == history

    def test_nonexistent(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        assert mgr.update_gemini_history("missing", []) is False


class TestSaveChat:
    """Test save_chat()."""

    def test_persists_changes(self, tmp_path):
        mgr = ChatManager(base_dir=str(tmp_path))
        chat = mgr.create_chat(name="Test", doc_ids=[])
        chat.doc_ids = ["d1", "d2"]
        mgr.save_chat(chat)
        loaded, _ = mgr.get_chat(chat.id)
        assert loaded.doc_ids == ["d1", "d2"]
