# Testing Guide

## Docker-Based Testing (Recommended)

All tests can be run in Docker for consistent, reproducible results.

### Quick Start

```bash
# Start services (Qdrant + Backend)
docker-compose up -d

# Run all tests
docker-compose run --rm test

# Stop services
docker-compose down
```

### Test Categories

#### 1. All Tests (Complete Suite)
```bash
docker-compose run --rm test
```

**Runs**: All 120+ tests across all test files
**Time**: ~2-5 minutes
**Requires**: Backend + Qdrant

---

#### 2. Unit Tests Only (Fast)
```bash
docker-compose run --rm unit-tests
```

**Runs**:
- `test_bm25_index.py` (~25 tests)
- `test_reranker.py` (~15 tests)

**Time**: ~30-60 seconds
**Requires**: Nothing (no external services)
**Best for**: Quick validation of BM25 and Reranker logic

---

#### 3. Integration Tests
```bash
docker-compose run --rm integration-tests
```

**Runs**:
- `test_hybrid_search.py` (~15 tests)
- `test_qa_guardrails.py` (~12 tests)
- `test_rag_pipeline_integration.py` (~15 tests)

**Time**: ~1-2 minutes
**Requires**: Qdrant only
**Best for**: Testing RAG pipeline components

---

#### 4. API Tests
```bash
docker-compose run --rm api-tests
```

**Runs**:
- `test_api.py` (existing API tests)
- `test_deleted_documents.py` (~15 tests)

**Time**: ~1-2 minutes
**Requires**: Backend + Qdrant
**Best for**: Testing REST API endpoints

---

## Local Testing (Without Docker)

### Prerequisites

```bash
# Install dependencies
pip install -r backend/requirements.txt
pip install -r backend/requirements-test.txt

# Start Qdrant
docker-compose up -d qdrant

# Start backend (in another terminal)
cd backend && python run_api.py
```

### Run Tests

```bash
cd backend

# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_bm25_index.py -v
pytest tests/test_reranker.py -v
pytest tests/test_hybrid_search.py -v
pytest tests/test_qa_guardrails.py -v
pytest tests/test_deleted_documents.py -v
pytest tests/test_rag_pipeline_integration.py -v
pytest tests/test_api.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Specific test
pytest tests/test_bm25_index.py::TestBM25Index::test_search_basic -v
```

---

## Test Categories Explained

### Unit Tests (40 tests)
**What**: Test individual components in isolation
**Files**: `test_bm25_index.py`, `test_reranker.py`
**No external dependencies**: Can run anywhere

### Integration Tests (42 tests)
**What**: Test components working together
**Files**: `test_hybrid_search.py`, `test_qa_guardrails.py`, `test_rag_pipeline_integration.py`
**Requires**: Qdrant vector database

### API Tests (40+ tests)
**What**: Test REST API endpoints end-to-end
**Files**: `test_api.py`, `test_deleted_documents.py`
**Requires**: Backend server + Qdrant

---

## Coverage Report

Generate HTML coverage report:

```bash
# With Docker
docker-compose run --rm test pytest tests/ --cov=src --cov-report=html

# Copy report from container
docker cp doc-qa-test:/app/htmlcov ./htmlcov

# Open report
open htmlcov/index.html  # macOS
```

**Coverage Target**: >85%

---

## Continuous Integration

For CI/CD pipelines:

```bash
# GitHub Actions example
docker-compose up -d
docker-compose run --rm test
docker-compose down
```

---

## Troubleshooting

### Tests fail with "Connection refused"

**Problem**: Qdrant or Backend not running
**Solution**:
```bash
docker-compose up -d
# Wait a few seconds for services to start
docker-compose run --rm test
```

### "GEMINI_API_KEY not configured"

**Problem**: Missing API key
**Solution**:
```bash
# Add to .env file
echo "GEMINI_API_KEY=your_key_here" >> backend/.env

# Or export
export GEMINI_API_KEY=your_key_here
```

### "Collection already exists" errors

**Problem**: Test data from previous runs
**Solution**:
```bash
# Clear test collections
docker-compose down -v
docker-compose up -d
```

### Tests hang or timeout

**Problem**: Services not responding
**Solution**:
```bash
# Check service health
docker-compose ps
docker-compose logs backend
docker-compose logs qdrant

# Restart if needed
docker-compose restart
```

---

## Test Development

### Adding New Tests

1. Create test file in `backend/tests/`
2. Use pytest fixtures from `conftest.py`
3. Follow naming convention: `test_*.py`
4. Run locally: `pytest tests/test_yourfile.py -v`
5. Update this guide if adding new test category

### Test Structure

```python
import pytest
from src.your_module import YourClass

@pytest.fixture
def your_fixture():
    """Fixture description."""
    instance = YourClass()
    yield instance
    # Cleanup if needed

class TestYourClass:
    """Test suite for YourClass."""

    def test_basic_functionality(self, your_fixture):
        """Test description."""
        result = your_fixture.method()
        assert result == expected
```

### Running Tests During Development

```bash
# Watch mode (re-run on file changes)
pytest-watch tests/

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -v -s

# Run last failed tests
pytest --lf
```

---

## Performance Benchmarks

| Test Category | Count | Time | Dependencies |
|--------------|-------|------|--------------|
| Unit Tests | 40 | ~45s | None |
| Integration Tests | 42 | ~90s | Qdrant |
| API Tests | 40+ | ~120s | Backend + Qdrant |
| **Total** | **120+** | **~4min** | Full stack |

*Times are approximate and may vary based on hardware*

---

## Next Steps

- Run tests before committing: `docker-compose run --rm test`
- Check coverage: `pytest tests/ --cov=src --cov-report=term`
- Add tests for new features
- Keep coverage above 85%
