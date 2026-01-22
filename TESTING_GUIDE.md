# Testing Guide - Backend API

Complete guide for testing the doc-qa-platform backend.

---

## Quick Start

### 1. Docker Testing (Recommended - No Python setup needed!)

```bash
# Start services
docker-compose up -d

# Run automated pytest suite
docker-compose run --rm test

# Or use helper script
cd backend
./run_tests.sh
```

### 2. Manual curl Testing (Quick checks)

```bash
# Start backend first
docker-compose up -d

# Run automated bash test script
cd backend
./test_api.sh /path/to/test.pdf

# Or run individual curls (see CURL_TESTS.md)
curl http://localhost:8000/health
```

---

## What Was Created

### 1. **CURL_TESTS.md** - Manual curl Commands
- Complete list of curl commands for every endpoint
- Copy-paste ready examples
- Expected responses
- Full test flow script

**Location:** `backend/CURL_TESTS.md`

### 2. **test_api.sh** - Automated Bash Script
- Tests all major endpoints in sequence
- Color-coded output (pass/fail)
- Automatic cleanup
- Shows IDs for manual testing

**Location:** `backend/test_api.sh`

**Usage:**
```bash
cd backend
./test_api.sh                           # Uses tests/fixtures/test.pdf
./test_api.sh /path/to/your/test.pdf   # Use custom PDF
```

### 3. **test_api.py** - Python Test Suite
- 19 comprehensive tests
- Organized by endpoint category
- Automatic fixtures and cleanup
- Page number verification

**Location:** `backend/tests/test_api.py`

**Usage (Docker - Recommended):**
```bash
# Run in Docker container
docker-compose run --rm test

# Specific test category
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# With output
docker-compose run --rm test pytest tests/test_api.py -v -s
```

---

## Test Coverage

### ✅ Health Check
- API status
- Qdrant connection
- Gemini configuration

### ✅ Document Management
- Upload PDF
- List documents
- Get document details
- Serve PDF file
- Delete document

### ✅ Chat Management
- Create chat (with/without docs)
- List all chats
- Get chat with messages
- Rename chat
- Delete chat

### ✅ Question Answering
- Ask in chat context
- Message persistence
- Source citations with page numbers
- Legacy query endpoint

### ✅ Error Handling
- 404 errors
- 422 validation errors
- Invalid file types

---

## Quick Reference

### Test Script Output

```bash
=== 1. Health Check ===
✓ Health check passed

=== 2. Upload Document ===
✓ Document uploaded with ID: abc123...

=== 8. Ask Question in Chat ===
✓ Got answer with 245 characters
✓ Sources include page numbers ✓

=== Test Summary ===
✓ All tests passed! 🎉
```

### pytest Output

```bash
tests/test_api.py::TestHealth::test_health_check PASSED
tests/test_api.py::TestDocuments::test_upload_document PASSED
tests/test_api.py::TestChats::test_create_chat PASSED
tests/test_api.py::TestChatQueries::test_ask_in_chat PASSED

==================== 19 passed in 45.23s ====================
```

---

## Comparison

| Method | Speed | Automation | Coverage | Setup | Best For |
|--------|-------|------------|----------|-------|----------|
| **Docker pytest** | Medium | Full | Comprehensive | None | Recommended, CI/CD |
| **test_api.sh** | Fast | Full | Good | None | Quick integration tests |
| **curl (manual)** | Fastest | Manual | Basic | None | Debugging specific endpoints |

---

## Common Test Scenarios

### Scenario 1: Quick Health Check
```bash
curl http://localhost:8000/health | jq
```

### Scenario 2: Test Full Flow
```bash
cd backend
./test_api.sh
```

### Scenario 3: Test Specific Feature
```bash
# Test only chat functionality
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# Test only document upload
docker-compose run --rm test pytest tests/test_api.py::TestDocuments::test_upload_document -v
```

### Scenario 4: Test with Your Own PDF
```bash
# Bash script
cd backend
./test_api.sh ~/Documents/mytest.pdf

# Copy to fixtures for pytest
cp ~/Documents/mytest.pdf backend/tests/fixtures/test.pdf
docker-compose run --rm test
```

---

## Troubleshooting

### Backend Not Running
```bash
# Start backend with Docker
docker-compose up -d

# Check if running
curl http://localhost:8000/health

# Check logs
docker-compose logs backend
```

### Qdrant Not Connected
```bash
# Start Qdrant
docker-compose up -d

# Check Qdrant
curl http://localhost:6333/collections
```

### Gemini Not Configured
```bash
# Add to .env
echo "GEMINI_API_KEY=your_key_here" >> backend/.env
```

### Test PDF Not Found
```bash
# Create fixtures directory
mkdir -p backend/tests/fixtures

# Copy your test PDF
cp /path/to/your.pdf backend/tests/fixtures/test.pdf

# reportlab is included in Docker image for auto-generation
```

### Page Numbers Not Showing
**Issue:** Old documents uploaded before page tracking update

**Solution:** Re-upload documents
```bash
curl -X POST http://localhost:8000/api/admin/upload \
  -F "file=@/path/to/document.pdf"
```

---

## CI/CD Integration

### GitHub Actions

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

      - name: Run tests
        run: |
          cd backend
          pytest tests/test_api.py -v
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

---

## Next Steps

1. **Start Services**
   ```bash
   docker-compose up -d
   ```

2. **Run Quick Test**
   ```bash
   cd backend
   ./test_api.sh
   ```

3. **Run Full Suite**
   ```bash
   docker-compose run --rm test
   ```

4. **Check Coverage**
   ```bash
   docker-compose run --rm test pytest tests/test_api.py --cov=src --cov-report=html
   ```

4. **Add Custom Tests**
   - Edit `tests/test_api.py`
   - Add new test methods to existing classes
   - Run specific tests with pytest

---

## Files Created

```
backend/
├── CURL_TESTS.md              # Manual curl commands
├── test_api.sh                # Automated bash script
├── requirements-test.txt      # Test dependencies
├── pytest.ini                 # pytest configuration
└── tests/
    ├── __init__.py
    ├── conftest.py           # pytest fixtures
    ├── test_api.py           # Main test suite
    ├── README.md             # Test documentation
    └── fixtures/
        └── test.pdf          # Test PDF (created if missing)
```

---

## Summary

✅ **3 Testing Methods Available:**
1. Docker pytest (`docker-compose run --rm test`) - **Recommended**
2. Bash script (`./test_api.sh`)
3. Manual curls (`CURL_TESTS.md`)

✅ **19 Automated Tests**
✅ **All Endpoints Covered**
✅ **Page Number Verification**
✅ **Automatic Cleanup**
✅ **No Local Python Setup Needed**
✅ **CI/CD Ready**

**Start testing:**
```bash
docker-compose up -d
docker-compose run --rm test
```
