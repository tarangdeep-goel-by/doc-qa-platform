# Backend Test Suite

Automated tests for doc-qa-platform backend API.

## Setup

### 1. Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### 2. Start Backend and Services

```bash
# Start Qdrant
docker-compose up -d

# Start backend (in another terminal)
python run_api.py
```

### 3. Set Environment Variables (Optional)

```bash
# Default values
export TEST_BASE_URL="http://localhost:8000"
export TEST_PDF_PATH="tests/fixtures/test.pdf"
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/test_api.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_api.py::TestDocuments -v
pytest tests/test_api.py::TestChats -v
pytest tests/test_api.py::TestChatQueries -v
```

### Run Specific Test

```bash
pytest tests/test_api.py::TestDocuments::test_upload_document -v
```

### Run with Output

```bash
pytest tests/test_api.py -v -s
```

### Run with Coverage

```bash
pytest tests/test_api.py --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in browser.

---

## Test Categories

### TestHealth
- Health check endpoint

### TestDocuments
- Upload document
- List documents
- Get document details
- Serve PDF file
- Delete document

### TestChats
- Create chat
- List chats
- Get chat with messages
- Rename chat
- Delete chat

### TestChatQueries
- Ask question in chat
- Message persistence
- Source citations with page numbers

### TestLegacyQuery
- Legacy /api/query/ask endpoint

### TestErrorCases
- 404 errors
- 422 validation errors
- Invalid file uploads

---

## Test Fixtures

### Automatic Fixtures

- **setup_test_environment**: Checks backend is running, creates dummy PDF
- **uploaded_doc_id**: Uploads document, returns ID, cleans up after
- **test_chat_id**: Creates chat, returns ID, cleans up after
- **test_chat_with_doc**: Creates chat with document, cleans up after

### Test PDF

If `tests/fixtures/test.pdf` doesn't exist, tests will create a dummy PDF using reportlab.

To use your own test PDF:
```bash
mkdir -p tests/fixtures
cp /path/to/your/test.pdf tests/fixtures/test.pdf
```

---

## Expected Results

All tests should pass if:
- ✅ Backend is running at http://localhost:8000
- ✅ Qdrant is running and accessible
- ✅ GEMINI_API_KEY is set in .env
- ✅ Test PDF exists or reportlab is installed

### Sample Output

```
tests/test_api.py::TestHealth::test_health_check PASSED
tests/test_api.py::TestDocuments::test_upload_document PASSED
tests/test_api.py::TestDocuments::test_list_documents PASSED
tests/test_api.py::TestDocuments::test_get_document_details PASSED
tests/test_api.py::TestDocuments::test_get_document_file PASSED
tests/test_api.py::TestDocuments::test_delete_document PASSED
tests/test_api.py::TestChats::test_create_chat PASSED
tests/test_api.py::TestChats::test_list_chats PASSED
tests/test_api.py::TestChats::test_get_chat PASSED
tests/test_api.py::TestChats::test_rename_chat PASSED
tests/test_api.py::TestChats::test_delete_chat PASSED
tests/test_api.py::TestChatQueries::test_ask_in_chat PASSED
tests/test_api.py::TestChatQueries::test_chat_message_persistence PASSED
tests/test_api.py::TestLegacyQuery::test_legacy_ask_endpoint PASSED
tests/test_api.py::TestErrorCases::test_get_nonexistent_document PASSED
tests/test_api.py::TestErrorCases::test_get_nonexistent_chat PASSED
tests/test_api.py::TestErrorCases::test_create_chat_invalid_payload PASSED
tests/test_api.py::TestErrorCases::test_ask_in_nonexistent_chat PASSED
tests/test_api.py::TestErrorCases::test_upload_non_pdf_file PASSED

==================== 19 passed in 45.23s ====================
```

---

## Troubleshooting

### ImportError: No module named pytest
```bash
pip install -r requirements-test.txt
```

### ConnectionError: Backend not running
```bash
# Start backend
python run_api.py
```

### Tests fail with "Qdrant not connected"
```bash
# Start Qdrant
docker-compose up -d

# Check Qdrant status
docker ps | grep qdrant
```

### Tests fail with "Gemini not configured"
```bash
# Add to .env file
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### Tests create dummy PDF but fail to process
```bash
# Provide a real test PDF
mkdir -p tests/fixtures
cp /path/to/real.pdf tests/fixtures/test.pdf
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Start backend
        run: |
          cd backend
          python run_api.py &
          sleep 10
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

      - name: Run tests
        run: |
          cd backend
          pytest tests/test_api.py -v
```

---

## Writing New Tests

### Example Test

```python
def test_my_feature(self):
    """Test description."""
    # Setup
    payload = {"data": "test"}

    # Execute
    response = requests.post(f"{BASE_URL}/api/endpoint", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "expected_value"
```

### Using Fixtures

```python
def test_with_fixture(self, uploaded_doc_id):
    """Test that uses uploaded document."""
    response = requests.get(f"{BASE_URL}/api/admin/documents/{uploaded_doc_id}")
    assert response.status_code == 200
```

---

## Performance Testing

For load testing, use `locust`:

```bash
pip install locust
locust -f tests/load_test.py --host=http://localhost:8000
```

(Create `tests/load_test.py` with locust scenarios)
