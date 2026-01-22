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
# Run complete test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Run Specific Test Files

```bash
# API integration tests
pytest tests/test_api.py -v

# BM25 keyword search tests
pytest tests/test_bm25_index.py -v

# Reranker tests
pytest tests/test_reranker.py -v

# Hybrid search tests
pytest tests/test_hybrid_search.py -v

# QA guardrails tests
pytest tests/test_qa_guardrails.py -v

# Deleted documents tests
pytest tests/test_deleted_documents.py -v

# Full pipeline integration tests
pytest tests/test_rag_pipeline_integration.py -v
```

### Run Specific Test Classes

```bash
# From test_api.py
pytest tests/test_api.py::TestDocuments -v
pytest tests/test_api.py::TestChats -v

# From new test files
pytest tests/test_bm25_index.py::TestBM25Index -v
pytest tests/test_reranker.py::TestReranker -v
pytest tests/test_hybrid_search.py::TestHybridSearch -v
```

### Run Specific Test

```bash
pytest tests/test_bm25_index.py::TestBM25Index::test_search_basic -v
pytest tests/test_reranker.py::TestReranker::test_rerank_improves_relevance -v
```

### Run with Output

```bash
pytest tests/ -v -s
```

### Run with Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Open report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Run Tests by Category

```bash
# Unit tests only (BM25, Reranker)
pytest tests/test_bm25_index.py tests/test_reranker.py -v

# Integration tests only (Hybrid search, Pipeline, API)
pytest tests/test_hybrid_search.py tests/test_rag_pipeline_integration.py -v

# API tests only
pytest tests/test_api.py tests/test_deleted_documents.py -v

# RAG improvements tests only
pytest tests/test_bm25_index.py tests/test_reranker.py tests/test_hybrid_search.py tests/test_qa_guardrails.py tests/test_rag_pipeline_integration.py -v
```

---

## Test Files Overview

### test_api.py - API Integration Tests
Core API endpoint tests covering:
- **TestHealth**: Health check endpoint
- **TestDocuments**: Document upload, list, details, serve, delete
- **TestChats**: Chat creation, listing, retrieval, renaming, deletion
- **TestChatQueries**: Asking questions, message persistence, source citations
- **TestLegacyQuery**: Legacy /api/query/ask endpoint
- **TestErrorCases**: 404 and 422 validation errors

### test_bm25_index.py - BM25 Keyword Search Tests
Unit tests for BM25 keyword-based search:
- Index initialization and building
- Basic search functionality
- Keyword matching and scoring
- Document filtering by doc_ids
- Top-k limit enforcement
- Cache save/load operations
- Case-insensitive search
- Score ordering and ranking
- Index rebuilding

**Coverage**: ~25 tests, >95% BM25Index coverage

### test_reranker.py - Cross-Encoder Reranker Tests
Unit tests for reranking with cross-encoder:
- Reranker initialization
- Basic reranking functionality
- Relevance improvement verification
- Score updates (rerank_score, retrieval_score)
- Empty chunks handling
- Top-k limit enforcement
- Metadata preservation
- Different query types
- Alternative chunk structures

**Coverage**: ~15 tests, >90% Reranker coverage

### test_hybrid_search.py - Hybrid Search Integration Tests
Integration tests for vector + BM25 hybrid search:
- Basic hybrid search
- Hybrid vs pure vector comparison
- Alpha parameter variations (0.0 to 1.0)
- Document filtering
- Keyword matching emphasis
- BM25 index rebuilding
- Search after document deletion
- Score normalization
- Cache persistence

**Coverage**: ~15 tests, hybrid search functionality

### test_qa_guardrails.py - QA Engine Guardrails Tests
Tests for production safety features:
- Min score threshold rejection/acceptance
- Low confidence query handling
- No results handling
- Hybrid search toggle
- Reranking toggle
- Improved prompt grounding
- Source metadata warnings
- Different min_score thresholds
- Alpha parameter variations
- Document filtering with guardrails

**Coverage**: ~12 tests, QA engine safety features

### test_deleted_documents.py - Deleted Documents API Tests
Tests for deleted document edge cases:
- Chat loading with existing documents
- Chat loading after document deletion
- Document deletion updates chat references
- Multiple chats affected by deletion
- Mixed documents (some deleted, some available)
- Available documents structure validation
- Asking questions with deleted docs
- Deletion message accuracy
- ChatDetailResponse schema validation

**Coverage**: ~15 tests, deleted document handling

### test_rag_pipeline_integration.py - Full Pipeline Integration Tests
End-to-end tests for complete RAG pipeline:
- Pure vector search pipeline
- Hybrid search pipeline
- Pipeline with reranking
- Guardrails pass/reject scenarios
- Document filtering
- Keyword vs semantic emphasis
- Retrieval count validation
- Source metadata preservation
- Empty/long query handling
- Multi-query consistency
- Performance baseline testing
- BM25 index persistence

**Coverage**: ~15 tests, full pipeline integration

---

## Total Test Coverage

**Test Files**: 7 files
**Total Tests**: ~120+ tests
**Code Coverage Target**: >85%

**Components Tested**:
- ✅ BM25Index (keyword search)
- ✅ Reranker (cross-encoder)
- ✅ VectorStore (hybrid search)
- ✅ QAEngine (with guardrails)
- ✅ API endpoints (with deleted docs handling)
- ✅ Full RAG pipeline (end-to-end)

---

## Original Test Categories (test_api.py)
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
