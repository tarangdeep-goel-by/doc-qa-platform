"""Extended API tests for untested HTTP endpoints.

Requires running backend + Qdrant (same as test_api.py).
"""

import json
import os
import time
import uuid
import pytest
import requests
from pathlib import Path


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_PDF_PATH = os.getenv("TEST_PDF_PATH", "tests/fixtures/test.pdf")


# ─── Helpers ───

def upload_doc():
    """Upload a test document, return doc_id."""
    pdf_path = Path(TEST_PDF_PATH)
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")
    with open(pdf_path, "rb") as f:
        resp = requests.post(f"{BASE_URL}/api/admin/upload", files={"file": (pdf_path.name, f, "application/pdf")})
    assert resp.status_code == 200
    return resp.json()["doc_id"]


def create_chat(name="Test Chat", doc_ids=None):
    """Create a chat, return chat response dict."""
    resp = requests.post(f"{BASE_URL}/api/chats", json={"name": name, "doc_ids": doc_ids or []})
    assert resp.status_code == 200
    return resp.json()


def delete_doc(doc_id):
    requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")


def delete_chat(chat_id):
    requests.delete(f"{BASE_URL}/api/chats/{chat_id}")


# ─── Bulk Delete Documents ───

class TestBulkDeleteDocuments:
    """Test POST /api/admin/documents/bulk-delete."""

    def test_all_exist(self):
        d1 = upload_doc()
        d2 = upload_doc()
        try:
            resp = requests.post(
                f"{BASE_URL}/api/admin/documents/bulk-delete",
                json={"doc_ids": [d1, d2]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            assert data["successful"] == 2
            assert data["failed"] == 0
        finally:
            delete_doc(d1)
            delete_doc(d2)

    def test_some_missing(self):
        d1 = upload_doc()
        try:
            resp = requests.post(
                f"{BASE_URL}/api/admin/documents/bulk-delete",
                json={"doc_ids": [d1, "nonexistent-id"]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["successful"] == 1
            assert data["failed"] == 1
        finally:
            delete_doc(d1)

    def test_empty_list_422(self):
        resp = requests.post(
            f"{BASE_URL}/api/admin/documents/bulk-delete",
            json={"doc_ids": []},
        )
        assert resp.status_code == 422


# ─── Admin Interactions / Feedback ───

class TestAdminObservability:
    """Test GET /api/admin/interactions and /api/admin/feedback."""

    def test_interactions_default(self):
        resp = requests.get(f"{BASE_URL}/api/admin/interactions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_interactions_with_limit(self):
        resp = requests.get(f"{BASE_URL}/api/admin/interactions", params={"limit": 5})
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_feedback_default(self):
        resp = requests.get(f"{BASE_URL}/api/admin/feedback")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_feedback_filter(self):
        resp = requests.get(f"{BASE_URL}/api/admin/feedback", params={"feedback": "up"})
        assert resp.status_code == 200


# ─── Bulk Delete Chats ───

class TestBulkDeleteChats:
    """Test POST /api/chats/bulk-delete."""

    def test_success(self):
        c1 = create_chat("Chat 1")
        c2 = create_chat("Chat 2")
        try:
            resp = requests.post(
                f"{BASE_URL}/api/chats/bulk-delete",
                json={"chat_ids": [c1["id"], c2["id"]]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["successful"] == 2
        finally:
            delete_chat(c1["id"])
            delete_chat(c2["id"])

    def test_some_missing(self):
        c1 = create_chat("Chat 1")
        try:
            resp = requests.post(
                f"{BASE_URL}/api/chats/bulk-delete",
                json={"chat_ids": [c1["id"], "nonexistent-id"]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["successful"] == 1
            assert data["failed"] == 1
        finally:
            delete_chat(c1["id"])

    def test_empty_list_422(self):
        resp = requests.post(
            f"{BASE_URL}/api/chats/bulk-delete",
            json={"chat_ids": []},
        )
        assert resp.status_code == 422


# ─── Update Chat Documents ───

class TestUpdateChatDocuments:
    """Test PUT /api/chats/{chat_id}/documents."""

    def test_replace(self):
        chat = create_chat("Test")
        try:
            resp = requests.put(
                f"{BASE_URL}/api/chats/{chat['id']}/documents",
                json={"doc_ids": ["new-doc-1", "new-doc-2"]},
            )
            assert resp.status_code == 200
            assert resp.json()["doc_ids"] == ["new-doc-1", "new-doc-2"]
        finally:
            delete_chat(chat["id"])

    def test_nonexistent_chat(self):
        resp = requests.put(
            f"{BASE_URL}/api/chats/nonexistent-id/documents",
            json={"doc_ids": []},
        )
        assert resp.status_code == 404


# ─── Remove Chat Document ───

class TestRemoveChatDocument:
    """Test DELETE /api/chats/{chat_id}/documents/{doc_id}."""

    def test_success(self):
        chat = create_chat("Test", doc_ids=["doc-a", "doc-b"])
        try:
            resp = requests.delete(
                f"{BASE_URL}/api/chats/{chat['id']}/documents/doc-a"
            )
            assert resp.status_code == 200
            assert "doc-a" not in resp.json()["doc_ids"]
            assert "doc-b" in resp.json()["doc_ids"]
        finally:
            delete_chat(chat["id"])

    def test_not_in_chat(self):
        chat = create_chat("Test", doc_ids=["doc-a"])
        try:
            resp = requests.delete(
                f"{BASE_URL}/api/chats/{chat['id']}/documents/doc-missing"
            )
            assert resp.status_code == 404
        finally:
            delete_chat(chat["id"])

    def test_nonexistent_chat(self):
        resp = requests.delete(
            f"{BASE_URL}/api/chats/nonexistent-id/documents/doc-a"
        )
        assert resp.status_code == 404


# ─── Message Feedback ───

class TestMessageFeedback:
    """Test POST /api/chats/{chat_id}/messages/{message_id}/feedback."""

    def test_nonexistent_chat(self):
        resp = requests.post(
            f"{BASE_URL}/api/chats/nonexistent/messages/msg1/feedback",
            json={"feedback": "up"},
        )
        assert resp.status_code == 404

    def test_nonexistent_message(self):
        chat = create_chat("Test")
        try:
            resp = requests.post(
                f"{BASE_URL}/api/chats/{chat['id']}/messages/nonexistent/feedback",
                json={"feedback": "up"},
            )
            assert resp.status_code == 404
        finally:
            delete_chat(chat["id"])


# ─── Validation ───

class TestValidation:
    """Test schema validation on requests."""

    def test_question_too_long(self):
        chat = create_chat("Test")
        try:
            resp = requests.post(
                f"{BASE_URL}/api/chats/{chat['id']}/ask",
                json={"question": "x" * 5001},
            )
            assert resp.status_code == 422
        finally:
            delete_chat(chat["id"])

    def test_chat_name_too_long(self):
        resp = requests.post(
            f"{BASE_URL}/api/chats",
            json={"name": "x" * 201, "doc_ids": []},
        )
        assert resp.status_code == 422

    def test_empty_question(self):
        chat = create_chat("Test")
        try:
            resp = requests.post(
                f"{BASE_URL}/api/chats/{chat['id']}/ask",
                json={"question": ""},
            )
            assert resp.status_code == 422
        finally:
            delete_chat(chat["id"])

    def test_empty_chat_name(self):
        resp = requests.post(
            f"{BASE_URL}/api/chats",
            json={"name": "", "doc_ids": []},
        )
        assert resp.status_code == 422
