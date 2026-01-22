"""Tests for deleted documents edge case handling."""

import pytest
import os


# Set to use requests for live API testing
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture
def client():
    """Test client - uses live API via requests."""
    import requests

    class APIClient:
        def __init__(self, base_url):
            self.base_url = base_url

        def post(self, path, **kwargs):
            return requests.post(f"{self.base_url}{path}", **kwargs)

        def get(self, path, **kwargs):
            return requests.get(f"{self.base_url}{path}", **kwargs)

        def delete(self, path, **kwargs):
            return requests.delete(f"{self.base_url}{path}", **kwargs)

    return APIClient(BASE_URL)


@pytest.fixture
def uploaded_doc(client):
    """Upload a test document and return its ID."""
    import uuid
    # Use unique filename to avoid duplicate detection
    unique_name = f"test_doc_{uuid.uuid4().hex[:8]}.pdf"

    with open("tests/fixtures/test.pdf", "rb") as f:
        response = client.post(
            "/api/admin/upload",
            files={"file": (unique_name, f, "application/pdf")}
        )

    assert response.status_code == 200, f"Upload failed: {response.json()}"
    return response.json()["doc_id"]


@pytest.fixture
def chat_with_doc(client, uploaded_doc):
    """Create a chat associated with the uploaded document."""
    response = client.post(
        "/api/chats",
        json={
            "name": "Test Chat",
            "doc_ids": [uploaded_doc]
        }
    )

    assert response.status_code == 200
    return response.json()


class TestDeletedDocuments:
    """Test suite for deleted documents handling."""

    def test_chat_with_existing_documents(self, client, chat_with_doc):
        """Test loading chat when all documents exist."""
        chat_id = chat_with_doc["id"]

        response = client.get(f"/api/chats/{chat_id}")

        assert response.status_code == 200
        data = response.json()

        # Should have no missing documents
        assert data["missing_documents"] == []
        # Should have available documents
        assert len(data["available_documents"]) > 0

    def test_chat_after_document_deleted(self, client, uploaded_doc, chat_with_doc):
        """Test loading chat after its document is deleted."""
        chat_id = chat_with_doc["id"]

        # Delete the document
        del_response = client.delete(f"/api/admin/documents/{uploaded_doc}")
        assert del_response.status_code == 200

        # Load chat
        response = client.get(f"/api/chats/{chat_id}")

        assert response.status_code == 200
        data = response.json()

        # Should show missing document
        assert uploaded_doc in data["missing_documents"]
        # Should have no available documents
        assert len(data["available_documents"]) == 0

    def test_delete_document_updates_chat_references(self, client, uploaded_doc, chat_with_doc):
        """Test that deleting document removes it from chat doc_ids."""
        chat_id = chat_with_doc["id"]

        # Verify chat has the document initially
        chat_response = client.get(f"/api/chats/{chat_id}")
        assert uploaded_doc in chat_response.json()["chat"]["doc_ids"]

        # Delete document
        del_response = client.delete(f"/api/admin/documents/{uploaded_doc}")
        assert del_response.status_code == 200

        # Check delete message mentions chat update
        assert "chat" in del_response.json()["message"].lower()

        # Verify chat no longer references the document
        updated_chat = client.get(f"/api/chats/{chat_id}").json()
        assert uploaded_doc not in updated_chat["chat"]["doc_ids"]

    def test_delete_document_multiple_chats(self, client, uploaded_doc):
        """Test deleting document that's in multiple chats."""
        # Create multiple chats with the same document
        chat1 = client.post(
            "/api/chats",
            json={"name": "Chat 1", "doc_ids": [uploaded_doc]}
        ).json()

        chat2 = client.post(
            "/api/chats",
            json={"name": "Chat 2", "doc_ids": [uploaded_doc]}
        ).json()

        # Delete document
        del_response = client.delete(f"/api/admin/documents/{uploaded_doc}")
        assert del_response.status_code == 200

        # Should mention multiple chats updated
        message = del_response.json()["message"]
        assert "2" in message or "chat" in message.lower()

        # Both chats should no longer have the document
        chat1_updated = client.get(f"/api/chats/{chat1['id']}").json()
        chat2_updated = client.get(f"/api/chats/{chat2['id']}").json()

        assert uploaded_doc not in chat1_updated["chat"]["doc_ids"]
        assert uploaded_doc not in chat2_updated["chat"]["doc_ids"]

    def test_chat_with_mixed_documents(self, client):
        """Test chat with some deleted and some existing documents."""
        import uuid
        # Upload two documents with unique names
        unique_id = uuid.uuid4().hex[:8]

        with open("tests/fixtures/test.pdf", "rb") as f:
            doc1_response = client.post(
                "/api/admin/upload",
                files={"file": (f"doc1_{unique_id}.pdf", f, "application/pdf")}
            )
        doc1_id = doc1_response.json()["doc_id"]

        with open("tests/fixtures/test.pdf", "rb") as f:
            doc2_response = client.post(
                "/api/admin/upload",
                files={"file": (f"doc2_{unique_id}.pdf", f, "application/pdf")}
            )
        doc2_id = doc2_response.json()["doc_id"]

        # Create chat with both documents
        chat = client.post(
            "/api/chats",
            json={"name": "Mixed Chat", "doc_ids": [doc1_id, doc2_id]}
        ).json()

        # Delete only doc1
        client.delete(f"/api/admin/documents/{doc1_id}")

        # Load chat
        response = client.get(f"/api/chats/{chat['id']}")
        data = response.json()

        # Should show one missing, one available
        assert doc1_id in data["missing_documents"]
        assert len(data["available_documents"]) == 1
        assert data["available_documents"][0]["doc_id"] == doc2_id

    def test_chat_available_documents_structure(self, client, uploaded_doc, chat_with_doc):
        """Test structure of available_documents field."""
        chat_id = chat_with_doc["id"]

        response = client.get(f"/api/chats/{chat_id}")
        data = response.json()

        # Check structure of available_documents
        available = data["available_documents"]
        assert len(available) > 0

        # Each should have doc_id and title
        for doc in available:
            assert "doc_id" in doc
            assert "title" in doc
            assert isinstance(doc["doc_id"], str)
            assert isinstance(doc["title"], str)

    def test_delete_nonexistent_document_chat_update(self, client, chat_with_doc):
        """Test that deleting nonexistent document doesn't break."""
        # Try to delete a nonexistent document
        response = client.delete("/api/admin/documents/nonexistent123")

        # Should return 404
        assert response.status_code == 404

    def test_chat_with_no_documents(self, client):
        """Test chat created with no documents."""
        # Create chat with empty doc_ids
        chat = client.post(
            "/api/chats",
            json={"name": "Empty Chat", "doc_ids": []}
        ).json()

        # Load chat
        response = client.get(f"/api/chats/{chat['id']}")
        data = response.json()

        # Should have no missing or available documents
        assert data["missing_documents"] == []
        assert data["available_documents"] == []

    def test_asking_in_chat_with_deleted_docs(self, client, uploaded_doc, chat_with_doc):
        """Test asking question in chat after document is deleted."""
        chat_id = chat_with_doc["id"]

        # Delete document
        client.delete(f"/api/admin/documents/{uploaded_doc}")

        # Try to ask question
        response = client.post(
            f"/api/chats/{chat_id}/ask",
            json={"question": "What is this document about?"}
        )

        # Should still work but return "no information" type answer
        assert response.status_code == 200
        answer = response.json()["message"]["content"]

        # Should indicate no information found
        assert "couldn't find" in answer.lower() or \
               "no information" in answer.lower() or \
               "don't have" in answer.lower()

    def test_delete_document_chat_list_still_works(self, client, uploaded_doc, chat_with_doc):
        """Test that chat list works after document deletion."""
        # Delete document
        client.delete(f"/api/admin/documents/{uploaded_doc}")

        # List chats
        response = client.get("/api/chats")

        assert response.status_code == 200
        chats = response.json()["chats"]
        assert len(chats) > 0

    def test_document_deletion_message_accuracy(self, client, uploaded_doc, chat_with_doc):
        """Test that deletion message accurately reports affected chats."""
        # Delete document
        response = client.delete(f"/api/admin/documents/{uploaded_doc}")

        message = response.json()["message"]

        # Should mention at least 1 chat
        assert "1" in message or "chat" in message.lower()

    def test_document_deletion_no_chats_affected(self, client, uploaded_doc):
        """Test deleting document that's not in any chats."""
        # Delete document (no chats created with it)
        response = client.delete(f"/api/admin/documents/{uploaded_doc}")

        assert response.status_code == 200
        message = response.json()["message"]

        # Should still succeed, message shouldn't mention chats
        # or should say 0 chats updated
        assert "deleted successfully" in message.lower()

    def test_chat_detail_response_schema(self, client, chat_with_doc):
        """Test that ChatDetailResponse includes new fields."""
        chat_id = chat_with_doc["id"]

        response = client.get(f"/api/chats/{chat_id}")
        data = response.json()

        # Required fields should exist
        assert "chat" in data
        assert "messages" in data
        assert "missing_documents" in data
        assert "available_documents" in data

        # Types should be correct
        assert isinstance(data["missing_documents"], list)
        assert isinstance(data["available_documents"], list)

    def test_multiple_document_deletions(self, client):
        """Test multiple sequential document deletions."""
        import uuid
        # Upload multiple documents with unique names
        doc_ids = []
        unique_id = uuid.uuid4().hex[:8]

        for i in range(3):
            with open("tests/fixtures/test.pdf", "rb") as f:
                response = client.post(
                    "/api/admin/upload",
                    files={"file": (f"doc{i}_{unique_id}.pdf", f, "application/pdf")}
                )
            assert response.status_code == 200, f"Upload {i} failed: {response.json()}"
            doc_ids.append(response.json()["doc_id"])

        # Create chat with all documents
        chat = client.post(
            "/api/chats",
            json={"name": "Multi Doc Chat", "doc_ids": doc_ids}
        ).json()

        # Delete documents one by one
        for doc_id in doc_ids:
            response = client.delete(f"/api/admin/documents/{doc_id}")
            assert response.status_code == 200

        # Final chat check
        final_chat = client.get(f"/api/chats/{chat['id']}").json()

        # All should be missing, none available
        assert len(final_chat["missing_documents"]) == 3
        assert len(final_chat["available_documents"]) == 0
