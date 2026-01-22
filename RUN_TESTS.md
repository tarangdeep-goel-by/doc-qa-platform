# How to Run Tests

## 🚀 Quick Start (After Building)

After running `docker-compose build backend`, here's how to run tests:

### Option 1: All Tests (Recommended)
```bash
docker-compose run --rm test
```

**What happens:**
1. Starts Qdrant and Backend containers
2. Waits for backend to be ready (~30 seconds max)
3. Runs all 107 tests
4. Takes ~10 minutes total

### Option 2: Unit Tests Only (Fast)
```bash
docker-compose run --rm unit-tests
```

**What happens:**
1. Runs only BM25 and Reranker tests
2. No external dependencies needed
3. Takes ~1 minute

### Option 3: Specific Test File
```bash
docker-compose run --rm test pytest tests/test_bm25_index.py -v
```

---

## 📋 Complete Workflow

### First Time Setup

```bash
# 1. Build Docker images
docker-compose build backend

# 2. Start services
docker-compose up -d

# 3. Run tests
docker-compose run --rm test
```

### After Code Changes

```bash
# 1. Rebuild only if you changed requirements.txt
docker-compose build backend

# 2. Restart services
docker-compose restart backend

# 3. Run tests
docker-compose run --rm test
```

### Daily Development

```bash
# Services already running, just run tests
docker-compose run --rm test

# Or run specific tests
docker-compose run --rm test pytest tests/test_bm25_index.py -v
```

---

## ⏱️ Test Timing

| Command | Time | What It Does |
|---------|------|--------------|
| `docker-compose run --rm unit-tests` | ~1 min | Fast unit tests (31 tests) |
| `docker-compose run --rm integration-tests` | ~5 min | RAG pipeline tests (43 tests) |
| `docker-compose run --rm api-tests` | ~2 min | API endpoint tests |
| `docker-compose run --rm test` | ~10 min | All 107 tests |

---

## 🔧 What Happens When You Run Tests

### `docker-compose run --rm test`

1. **Starts dependencies** (if not running):
   - Qdrant on port 6333
   - Backend on port 8000

2. **Waits for backend** (automatic):
   - Retries health check for up to 30 seconds
   - Shows progress: "Waiting for backend to start... (1/30)"
   - Fails if backend doesn't start

3. **Runs tests**:
   - All test files in `tests/` directory
   - Shows progress and results

4. **Cleanup**:
   - Test container removed (`--rm` flag)
   - Backend and Qdrant keep running

---

## ✅ Expected Output

```
=== Setting up test environment ===
  Waiting for backend to start... (1/30)
  Waiting for backend to start... (2/30)
✓ Backend is running at http://backend:8000

============================= test session starts ==============================
...
tests/test_bm25_index.py::TestBM25Index::test_initialization PASSED      [  1%]
tests/test_bm25_index.py::TestBM25Index::test_build_index PASSED         [  2%]
...
======================== 107 passed in 544.97s ===============================
```

---

## ❌ Troubleshooting

### "Backend did not start after 30 seconds"

**Cause**: Backend container crashed or failed to start

**Fix**:
```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - GEMINI_API_KEY not set
# - Qdrant not running
# - Port 8000 already in use

# Restart backend
docker-compose restart backend

# Or rebuild
docker-compose build backend
docker-compose up -d
```

### "Connection refused" to Qdrant

**Cause**: Qdrant not running

**Fix**:
```bash
# Start Qdrant
docker-compose up -d qdrant

# Check status
docker-compose ps
```

### "ModuleNotFoundError: No module named 'rank_bm25'"

**Cause**: Docker image not rebuilt after adding dependencies

**Fix**:
```bash
docker-compose build backend --no-cache
```

### Tests hang or timeout

**Cause**: Model download or Gemini API slow

**Fix**:
- First run takes longer (downloading models)
- Subsequent runs are faster (models cached)
- Integration tests can take 5+ minutes (this is normal)

---

## 🎯 Best Practices

### Daily Workflow

```bash
# Morning: Start services
docker-compose up -d

# Make code changes...

# Run relevant tests
docker-compose run --rm unit-tests  # Fast feedback

# Before commit: Run all tests
docker-compose run --rm test

# Evening: Stop services
docker-compose down
```

### CI/CD Workflow

```bash
# Clean build and test
docker-compose down -v
docker-compose build backend
docker-compose up -d
sleep 10  # Give backend time to start
docker-compose run --rm test
docker-compose down
```

---

## 📊 Test Categories

### Unit Tests (No Dependencies)
- `test_bm25_index.py` - BM25 keyword search
- `test_reranker.py` - Cross-encoder reranking

### Integration Tests (Needs Qdrant)
- `test_hybrid_search.py` - Vector + BM25 hybrid search
- `test_qa_guardrails.py` - QA engine safety features
- `test_rag_pipeline_integration.py` - Full pipeline tests

### API Tests (Needs Backend + Qdrant)
- `test_api.py` - REST API endpoints
- `test_deleted_documents.py` - Deleted document handling

---

## 🔍 Running Specific Tests

```bash
# Single test file
docker-compose run --rm test pytest tests/test_bm25_index.py -v

# Single test class
docker-compose run --rm test pytest tests/test_api.py::TestHealth -v

# Single test method
docker-compose run --rm test pytest tests/test_api.py::TestHealth::test_health_check -v

# With coverage
docker-compose run --rm test pytest tests/ --cov=src --cov-report=term

# Stop on first failure
docker-compose run --rm test pytest tests/ -x

# Show print statements
docker-compose run --rm test pytest tests/ -v -s
```

---

## 📝 Summary

**After `docker-compose build backend`, run:**

```bash
docker-compose run --rm test
```

**That's it!** The test runner will:
- Start backend/Qdrant if needed
- Wait for backend to be ready
- Run all tests
- Show results

For faster feedback during development, use:
```bash
docker-compose run --rm unit-tests  # Just 1 minute!
```
