"""
Automated test suite for doc-qa-platform backend API.

Run with:
    pytest tests/test_api.py -v
    pytest tests/test_api.py -v -s  # with print output
    pytest tests/test_api.py::TestDocuments -v  # specific test class
"""

import pytest
import requests
import os
import time
from pathlib import Path

# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_PDF_PATH = os.getenv("TEST_PDF_PATH", "tests/fixtures/test.pdf")


class TestHealth:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test GET /health returns healthy status."""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "qdrant_connected" in data
        assert "gemini_configured" in data

        # For tests to pass, both should be true
        assert data["qdrant_connected"] is True, "Qdrant is not connected"
        assert data["gemini_configured"] is True, "Gemini API key not configured"


class TestDocuments:
    """Test document management endpoints."""

    @pytest.fixture
    def uploaded_doc_id(self):
        """Fixture that uploads a document and returns its ID, cleans up after test."""
        # Create a simple test PDF if it doesn't exist
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        # Upload document
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        doc_id = data["doc_id"]

        yield doc_id

        # Cleanup: delete document
        requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")

    def test_upload_document(self):
        """Test POST /api/admin/upload uploads a document successfully."""
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        assert "doc_id" in data
        assert "title" in data
        assert data["status"] == "success"
        assert "chunk_count" in data
        assert data["chunk_count"] > 0
        assert "processing_time" in data

        # Cleanup
        doc_id = data["doc_id"]
        requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")

    def test_list_documents(self, uploaded_doc_id):
        """Test GET /api/admin/documents returns document list."""
        response = requests.get(f"{BASE_URL}/api/admin/documents")
        assert response.status_code == 200

        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

        # Verify our uploaded document is in the list
        doc_ids = [doc["doc_id"] for doc in data["documents"]]
        assert uploaded_doc_id in doc_ids

    def test_get_document_details(self, uploaded_doc_id):
        """Test GET /api/admin/documents/{doc_id} returns document details."""
        response = requests.get(f"{BASE_URL}/api/admin/documents/{uploaded_doc_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["doc_id"] == uploaded_doc_id
        assert "title" in data
        assert "filename" in data
        assert "format" in data
        assert "chunk_count" in data
        assert "total_pages" in data
        assert "metadata" in data

    def test_get_document_file(self, uploaded_doc_id):
        """Test GET /api/admin/documents/{doc_id}/file serves PDF."""
        response = requests.get(f"{BASE_URL}/api/admin/documents/{uploaded_doc_id}/file")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0

    def test_delete_document(self):
        """Test DELETE /api/admin/documents/{doc_id} removes document."""
        # Upload a document
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            upload_response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        doc_id = upload_response.json()["doc_id"]

        # Delete it
        response = requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "message" in data

        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/admin/documents/{doc_id}")
        assert get_response.status_code == 404


class TestChats:
    """Test chat management endpoints."""

    @pytest.fixture
    def test_chat_id(self):
        """Fixture that creates a chat and returns its ID, cleans up after test."""
        payload = {
            "name": "Test Chat",
            "doc_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/chats", json=payload)
        assert response.status_code == 200
        chat_id = response.json()["id"]

        yield chat_id

        # Cleanup: delete chat
        requests.delete(f"{BASE_URL}/api/chats/{chat_id}")

    def test_create_chat(self):
        """Test POST /api/chats creates a new chat."""
        payload = {
            "name": "Integration Test Chat",
            "doc_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/chats", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["name"] == "Integration Test Chat"
        assert data["doc_ids"] == []
        assert data["message_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data

        # Cleanup
        requests.delete(f"{BASE_URL}/api/chats/{data['id']}")

    def test_list_chats(self, test_chat_id):
        """Test GET /api/chats returns chat list."""
        response = requests.get(f"{BASE_URL}/api/chats")
        assert response.status_code == 200

        data = response.json()
        assert "chats" in data
        assert isinstance(data["chats"], list)

        # Verify our test chat is in the list
        chat_ids = [chat["id"] for chat in data["chats"]]
        assert test_chat_id in chat_ids

    def test_get_chat(self, test_chat_id):
        """Test GET /api/chats/{chat_id} returns chat with messages."""
        response = requests.get(f"{BASE_URL}/api/chats/{test_chat_id}")
        assert response.status_code == 200

        data = response.json()
        assert "chat" in data
        assert "messages" in data

        chat = data["chat"]
        assert chat["id"] == test_chat_id
        assert chat["name"] == "Test Chat"

        messages = data["messages"]
        assert isinstance(messages, list)

    def test_rename_chat(self, test_chat_id):
        """Test PATCH /api/chats/{chat_id} renames chat."""
        payload = {"name": "Renamed Test Chat"}
        response = requests.patch(f"{BASE_URL}/api/chats/{test_chat_id}", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == test_chat_id
        assert data["name"] == "Renamed Test Chat"

    def test_delete_chat(self):
        """Test DELETE /api/chats/{chat_id} removes chat."""
        # Create a chat
        payload = {"name": "Chat to Delete", "doc_ids": []}
        create_response = requests.post(f"{BASE_URL}/api/chats", json=payload)
        chat_id = create_response.json()["id"]

        # Delete it
        response = requests.delete(f"{BASE_URL}/api/chats/{chat_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/chats/{chat_id}")
        assert get_response.status_code == 404


class TestChatQueries:
    """Test asking questions in chat context."""

    @pytest.fixture
    def test_chat_with_doc(self):
        """Fixture that creates a chat with a document."""
        # Upload document
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            upload_response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        doc_id = upload_response.json()["doc_id"]

        # Create chat with document
        payload = {
            "name": "Query Test Chat",
            "doc_ids": [doc_id]
        }
        chat_response = requests.post(f"{BASE_URL}/api/chats", json=payload)
        chat_id = chat_response.json()["id"]

        yield {"chat_id": chat_id, "doc_id": doc_id}

        # Cleanup
        requests.delete(f"{BASE_URL}/api/chats/{chat_id}")
        requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")

    def test_ask_in_chat(self, test_chat_with_doc):
        """Test POST /api/chats/{chat_id}/ask sends question and gets answer."""
        chat_id = test_chat_with_doc["chat_id"]

        payload = {
            "question": "What is this document about?",
            "top_k": 5
        }
        response = requests.post(f"{BASE_URL}/api/chats/{chat_id}/ask", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data

        message = data["message"]
        assert "id" in message
        assert message["chat_id"] == chat_id
        assert message["role"] == "assistant"
        assert "content" in message
        assert len(message["content"]) > 0
        assert "timestamp" in message

        # Check sources
        if message.get("sources"):
            assert isinstance(message["sources"], list)
            for source in message["sources"]:
                assert "doc_id" in source
                assert "doc_title" in source
                assert "score" in source
                # Page number should be present for new uploads
                assert "page_num" in source

    def test_chat_message_persistence(self, test_chat_with_doc):
        """Test that messages persist in chat."""
        chat_id = test_chat_with_doc["chat_id"]

        # Ask a question
        payload = {"question": "Test question", "top_k": 5}
        requests.post(f"{BASE_URL}/api/chats/{chat_id}/ask", json=payload)

        # Wait a bit for processing
        time.sleep(0.5)

        # Get chat and verify messages
        response = requests.get(f"{BASE_URL}/api/chats/{chat_id}")
        assert response.status_code == 200

        data = response.json()
        messages = data["messages"]

        # Should have at least 2 messages (user + assistant)
        assert len(messages) >= 2

        # Verify message structure
        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "Test question"

        assistant_msg = next(m for m in messages if m["role"] == "assistant")
        assert len(assistant_msg["content"]) > 0


class TestLegacyQuery:
    """Test legacy query endpoint (still supported)."""

    @pytest.fixture
    def uploaded_doc_id(self):
        """Upload a test document."""
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        doc_id = response.json()["doc_id"]
        yield doc_id
        requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")

    def test_legacy_ask_endpoint(self, uploaded_doc_id):
        """Test POST /api/query/ask (legacy endpoint)."""
        payload = {
            "question": "What is this about?",
            "top_k": 5,
            "doc_ids": [uploaded_doc_id]
        }
        response = requests.post(f"{BASE_URL}/api/query/ask", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["question"] == "What is this about?"
        assert "answer" in data
        assert "sources" in data
        assert "retrieved_count" in data

        # Verify sources have page numbers
        for source in data["sources"]:
            assert "page_num" in source


class TestQueryDocuments:
    """Test /api/query/documents endpoint with chat usage information."""

    @pytest.fixture
    def uploaded_doc_id(self):
        """Fixture that uploads a document and returns its ID."""
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

        assert response.status_code == 200
        doc_id = response.json()["doc_id"]

        yield doc_id

        # Cleanup
        requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")

    def test_query_documents_basic(self, uploaded_doc_id):
        """Test GET /api/query/documents returns correct structure."""
        response = requests.get(f"{BASE_URL}/api/query/documents")
        assert response.status_code == 200

        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

        # Find our uploaded document
        doc = None
        for d in data["documents"]:
            if d["doc_id"] == uploaded_doc_id:
                doc = d
                break

        assert doc is not None, "Uploaded document not found in response"

        # Verify all expected fields
        assert "doc_id" in doc
        assert "title" in doc
        assert "upload_date" in doc
        assert "file_size_mb" in doc
        assert "chunk_count" in doc
        assert "format" in doc
        assert "chat_count" in doc
        assert "chats" in doc

        # Verify types
        assert isinstance(doc["chat_count"], int)
        assert isinstance(doc["chats"], list)

    def test_query_documents_no_chats(self, uploaded_doc_id):
        """Test document shows chat_count=0 when not used in any chat."""
        response = requests.get(f"{BASE_URL}/api/query/documents")
        assert response.status_code == 200

        data = response.json()
        doc = next((d for d in data["documents"] if d["doc_id"] == uploaded_doc_id), None)

        assert doc is not None
        assert doc["chat_count"] == 0
        assert doc["chats"] == []

    def test_query_documents_single_chat(self, uploaded_doc_id):
        """Test document shows chat_count=1 when used in 1 chat."""
        # Create chat with this document
        chat_payload = {
            "name": "Test Chat Single",
            "doc_ids": [uploaded_doc_id]
        }
        chat_response = requests.post(f"{BASE_URL}/api/chats", json=chat_payload)
        assert chat_response.status_code == 200
        chat_id = chat_response.json()["id"]

        try:
            # Query documents
            response = requests.get(f"{BASE_URL}/api/query/documents")
            assert response.status_code == 200

            data = response.json()
            doc = next((d for d in data["documents"] if d["doc_id"] == uploaded_doc_id), None)

            assert doc is not None
            assert doc["chat_count"] == 1
            assert len(doc["chats"]) == 1
            assert doc["chats"][0]["id"] == chat_id
            assert doc["chats"][0]["name"] == "Test Chat Single"

        finally:
            # Cleanup chat
            requests.delete(f"{BASE_URL}/api/chats/{chat_id}")

    def test_query_documents_multiple_chats(self, uploaded_doc_id):
        """Test document shows chat_count=3 when used in 3 chats."""
        chat_ids = []

        try:
            # Create 3 chats with this document
            for i in range(3):
                chat_payload = {
                    "name": f"Test Chat {i+1}",
                    "doc_ids": [uploaded_doc_id]
                }
                chat_response = requests.post(f"{BASE_URL}/api/chats", json=chat_payload)
                assert chat_response.status_code == 200
                chat_ids.append(chat_response.json()["id"])

            # Query documents
            response = requests.get(f"{BASE_URL}/api/query/documents")
            assert response.status_code == 200

            data = response.json()
            doc = next((d for d in data["documents"] if d["doc_id"] == uploaded_doc_id), None)

            assert doc is not None
            assert doc["chat_count"] == 3
            assert len(doc["chats"]) == 3

            # Verify all chat IDs are present
            returned_chat_ids = [c["id"] for c in doc["chats"]]
            for chat_id in chat_ids:
                assert chat_id in returned_chat_ids

        finally:
            # Cleanup chats
            for chat_id in chat_ids:
                requests.delete(f"{BASE_URL}/api/chats/{chat_id}")

    def test_query_documents_mixed_usage(self):
        """Test correct chat counts across multiple documents with different usage."""
        pdf_path = Path(TEST_PDF_PATH)
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found at {TEST_PDF_PATH}")

        doc_ids = []
        chat_ids = []

        try:
            # Upload 2 documents (with different filenames to avoid conflicts)
            for i in range(2):
                with open(pdf_path, 'rb') as f:
                    # Use different filenames to avoid duplicate detection
                    filename = f"test_doc_{i}.pdf"
                    files = {'file': (filename, f, 'application/pdf')}
                    response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)
                assert response.status_code == 200, f"Upload failed: {response.json()}"
                doc_ids.append(response.json()["doc_id"])

            doc_a, doc_b = doc_ids[0], doc_ids[1]

            # Create chat 1 with doc A only
            chat1_payload = {"name": "Chat A Only", "doc_ids": [doc_a]}
            chat1_response = requests.post(f"{BASE_URL}/api/chats", json=chat1_payload)
            assert chat1_response.status_code == 200
            chat_ids.append(chat1_response.json()["id"])

            # Create chat 2 with doc B only
            chat2_payload = {"name": "Chat B Only", "doc_ids": [doc_b]}
            chat2_response = requests.post(f"{BASE_URL}/api/chats", json=chat2_payload)
            assert chat2_response.status_code == 200
            chat_ids.append(chat2_response.json()["id"])

            # Create chat 3 with both docs
            chat3_payload = {"name": "Chat A+B", "doc_ids": [doc_a, doc_b]}
            chat3_response = requests.post(f"{BASE_URL}/api/chats", json=chat3_payload)
            assert chat3_response.status_code == 200
            chat_ids.append(chat3_response.json()["id"])

            # Query documents
            response = requests.get(f"{BASE_URL}/api/query/documents")
            assert response.status_code == 200

            data = response.json()

            # Find both documents
            doc_a_data = next((d for d in data["documents"] if d["doc_id"] == doc_a), None)
            doc_b_data = next((d for d in data["documents"] if d["doc_id"] == doc_b), None)

            assert doc_a_data is not None
            assert doc_b_data is not None

            # Verify doc A has chat_count=2 (chats 1 and 3)
            assert doc_a_data["chat_count"] == 2
            assert len(doc_a_data["chats"]) == 2
            doc_a_chat_ids = [c["id"] for c in doc_a_data["chats"]]
            assert chat_ids[0] in doc_a_chat_ids  # Chat 1
            assert chat_ids[2] in doc_a_chat_ids  # Chat 3

            # Verify doc B has chat_count=2 (chats 2 and 3)
            assert doc_b_data["chat_count"] == 2
            assert len(doc_b_data["chats"]) == 2
            doc_b_chat_ids = [c["id"] for c in doc_b_data["chats"]]
            assert chat_ids[1] in doc_b_chat_ids  # Chat 2
            assert chat_ids[2] in doc_b_chat_ids  # Chat 3

        finally:
            # Cleanup chats
            for chat_id in chat_ids:
                requests.delete(f"{BASE_URL}/api/chats/{chat_id}")

            # Cleanup documents
            for doc_id in doc_ids:
                requests.delete(f"{BASE_URL}/api/admin/documents/{doc_id}")


class TestErrorCases:
    """Test error handling."""

    def test_get_nonexistent_document(self):
        """Test GET for non-existent document returns 404."""
        response = requests.get(f"{BASE_URL}/api/admin/documents/nonexistent-id")
        assert response.status_code == 404

    def test_get_nonexistent_chat(self):
        """Test GET for non-existent chat returns 404."""
        response = requests.get(f"{BASE_URL}/api/chats/nonexistent-id")
        assert response.status_code == 404

    def test_create_chat_invalid_payload(self):
        """Test POST /api/chats with invalid payload returns 422."""
        payload = {"invalid": "data"}
        response = requests.post(f"{BASE_URL}/api/chats", json=payload)
        assert response.status_code == 422

    def test_ask_in_nonexistent_chat(self):
        """Test asking question in non-existent chat returns 404."""
        payload = {"question": "test", "top_k": 5}
        response = requests.post(f"{BASE_URL}/api/chats/nonexistent-id/ask", json=payload)
        assert response.status_code == 404

    def test_upload_non_pdf_file(self):
        """Test uploading non-PDF file returns 400."""
        # Create a simple text file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a PDF")
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = requests.post(f"{BASE_URL}/api/admin/upload", files=files)

            assert response.status_code == 400
        finally:
            os.unlink(temp_path)


# Optional: Add fixtures for test data setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    import time

    print("\n=== Setting up test environment ===")

    # Check if backend is running (retry with timeout for Docker startup)
    max_retries = 30  # 30 seconds total
    retry_delay = 1  # 1 second between retries

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Backend is running at {BASE_URL}")
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                print(f"  Waiting for backend to start... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                pytest.exit(f"Backend did not start at {BASE_URL} after {max_retries} seconds. Check logs with: docker-compose logs backend")

    # Create test fixtures directory
    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy PDF if it doesn't exist
    if not Path(TEST_PDF_PATH).exists():
        print(f"Creating dummy test PDF at {TEST_PDF_PATH}")
        create_dummy_pdf(TEST_PDF_PATH)

    yield

    print("\n=== Test environment cleanup complete ===")


def create_dummy_pdf(path: str):
    """Create a simple test PDF using reportlab."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(100, 750, "Test Document")
        c.drawString(100, 730, "This is a test document for API testing.")
        c.drawString(100, 710, "Page 1 content.")
        c.showPage()

        c.drawString(100, 750, "Page 2")
        c.drawString(100, 730, "This is page 2 of the test document.")
        c.showPage()

        c.save()
        print(f"Created test PDF at {path}")
    except ImportError:
        print("reportlab not installed. Please provide a test PDF or install reportlab.")
        print("pip install reportlab")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "-s"])
