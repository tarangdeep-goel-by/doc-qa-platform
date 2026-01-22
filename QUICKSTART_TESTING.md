# Quick Start - Testing

## 🚀 Fastest Way to Run Tests

### Step 1: Rebuild Docker (First time or after dependency changes)
```bash
docker-compose build backend
```

### Step 2: Run Tests
```bash
# Start services
docker-compose up -d

# Run all tests
docker-compose run --rm test
```

**That's it!** ✅

---

## 📋 Test Commands

### All Tests (Recommended)
```bash
./run_tests_docker.sh
```

This script:
1. Rebuilds backend image
2. Starts services
3. Runs complete test suite
4. Shows results

### Individual Test Categories

**Unit Tests (fastest, no dependencies)**
```bash
docker-compose run --rm unit-tests
```

**Integration Tests (needs Qdrant)**
```bash
docker-compose up -d qdrant
docker-compose run --rm integration-tests
```

**API Tests (needs backend + Qdrant)**
```bash
docker-compose up -d
docker-compose run --rm api-tests
```

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'rank_bm25'"

**Fix**: Rebuild Docker image
```bash
docker-compose build backend --no-cache
```

### "ImportError: cannot import name 'create_app'"

**Fix**: Already fixed in latest commit
```bash
git pull
docker-compose build backend
```

### "Connection refused" errors

**Fix**: Ensure services are running
```bash
docker-compose up -d
sleep 5  # Wait for startup
docker-compose run --rm test
```

### Tests hang or timeout

**Fix**: Restart services
```bash
docker-compose down
docker-compose up -d
docker-compose run --rm test
```

---

## ✅ Expected Results

**Successful run shows:**
```
============================= test session starts ==============================
collected 120+ items

tests/test_bm25_index.py::TestBM25Index::test_initialization PASSED     [  1%]
tests/test_bm25_index.py::TestBM25Index::test_build_index PASSED        [  2%]
...
tests/test_rag_pipeline_integration.py::... PASSED                      [100%]

======================== 120 passed in 240s ===============================
```

**Coverage > 85%** ✅

---

## 🎯 Quick Reference

| Command | What it does | Time | Needs |
|---------|-------------|------|-------|
| `./run_tests_docker.sh` | Everything | ~4min | Docker |
| `docker-compose run --rm test` | All tests | ~4min | Services running |
| `docker-compose run --rm unit-tests` | Fast tests | ~45s | Nothing |
| `docker-compose run --rm integration-tests` | RAG tests | ~90s | Qdrant |
| `docker-compose run --rm api-tests` | API tests | ~120s | Backend + Qdrant |

---

## 📚 More Info

See [TESTING.md](TESTING.md) for comprehensive guide.
