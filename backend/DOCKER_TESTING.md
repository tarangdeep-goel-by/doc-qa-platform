# Docker-Based Testing Guide

Test the backend API using Docker containers - no local Python environment needed!

---

## Quick Start

### 1. Start Services

```bash
# Start backend and Qdrant
docker-compose up -d
```

### 2. Run Tests

```bash
# Run pytest suite in Docker
docker-compose run --rm test

# Or use the helper script
./run_tests.sh
```

---

## What's Included

### Test Dependencies (in Docker)
- pytest
- pytest-cov
- requests
- reportlab

All dependencies are installed in the Docker image automatically.

### Test Service
The `docker-compose.yml` includes a `test` service that:
- Uses the same backend image
- Connects to the backend and Qdrant containers
- Runs pytest automatically
- Cleans up after completion (`--rm` flag)

---

## Running Tests

### Method 1: Direct Docker Compose

```bash
# Run all tests
docker-compose run --rm test

# Run specific test class
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# Run with output
docker-compose run --rm test pytest tests/test_api.py -v -s

# Run with coverage
docker-compose run --rm test pytest tests/test_api.py --cov=src --cov-report=html
```

### Method 2: Helper Script

```bash
# Simple wrapper around docker-compose
./run_tests.sh
```

### Method 3: Bash Script (Manual Testing)

```bash
# For quick manual testing without pytest
./test_api.sh /path/to/test.pdf
```

---

## Test Output

### Successful Run
```
=== Running Backend Tests in Docker ===

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

=== Tests Complete ===
```

---

## Architecture

```
┌─────────────────┐
│  Test Container │
│   (pytest)      │
└────────┬────────┘
         │ HTTP requests
         ↓
┌─────────────────┐     ┌─────────────────┐
│ Backend         │────→│ Qdrant          │
│ Container       │     │ Container       │
└─────────────────┘     └─────────────────┘
```

The test container:
- Connects to `backend` service via Docker network
- Uses `http://backend:8000` as base URL
- Shares the same network as backend and Qdrant

---

## Rebuilding After Changes

If you modify code or dependencies:

```bash
# Rebuild backend image
docker-compose build backend

# Or rebuild everything
docker-compose build

# Then run tests
docker-compose run --rm test
```

---

## Troubleshooting

### Backend not running
```bash
# Check container status
docker-compose ps

# Start backend
docker-compose up -d backend

# Check logs
docker-compose logs backend
```

### Tests can't connect to backend
```bash
# Ensure backend is healthy
curl http://localhost:8000/health

# Check if containers are on same network
docker network inspect doc-qa-platform_default
```

### Qdrant connection issues
```bash
# Check Qdrant status
docker-compose ps qdrant

# Restart Qdrant
docker-compose restart qdrant

# Check logs
docker-compose logs qdrant
```

### Test PDF not found
```bash
# Create fixtures directory
mkdir -p tests/fixtures

# Add your test PDF
cp /path/to/test.pdf tests/fixtures/test.pdf
```

---

## CI/CD with Docker

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Create .env file
        run: |
          echo "GEMINI_API_KEY2=${{ secrets.GEMINI_API_KEY }}" > .env

      - name: Build and start services
        run: |
          docker-compose up -d backend
          sleep 10

      - name: Run tests
        run: docker-compose run --rm test
```

---

## Local Development Testing

### Option 1: Docker (Recommended)
```bash
docker-compose up -d
docker-compose run --rm test
```

**Pros:**
- No local Python setup needed
- Consistent environment
- Matches production

**Cons:**
- Slower for rapid iteration
- Need to rebuild after code changes

### Option 2: Bash Script (Quick Tests)
```bash
docker-compose up -d
./test_api.sh
```

**Pros:**
- Very fast
- Good for quick checks
- No pytest needed

**Cons:**
- Less comprehensive
- Manual validation

### Option 3: API Docs (Manual)
```bash
# Open interactive API docs
open http://localhost:8000/docs

# Test endpoints manually
```

**Pros:**
- Visual interface
- Great for debugging
- Real-time testing

**Cons:**
- Not automated
- Time-consuming

---

## Commands Summary

```bash
# Start services
docker-compose up -d

# Run all tests
docker-compose run --rm test

# Run specific tests
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# Run bash test script
./test_api.sh

# View backend logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild and test
docker-compose build backend && docker-compose run --rm test
```

---

## Files

- **docker-compose.yml** - Test service definition
- **Dockerfile** - Includes test dependencies
- **requirements.txt** - Combined app + test dependencies
- **run_tests.sh** - Helper script for running tests
- **test_api.sh** - Bash script for manual testing
- **tests/test_api.py** - Pytest test suite (19 tests)

---

## Next Steps

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Run tests:**
   ```bash
   docker-compose run --rm test
   ```

3. **View results:**
   - All tests should pass if backend and Qdrant are healthy
   - Check test output for any failures
   - Use `docker-compose logs backend` for debugging

**No local Python environment needed! 🎉**
