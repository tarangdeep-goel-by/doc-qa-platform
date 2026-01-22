# Testing - Quick Reference

## 🚀 Quick Start (Docker - No Python Setup!)

```bash
# 1. Start services
docker-compose up -d

# 2. Run tests
docker-compose run --rm test
```

That's it! All dependencies are in Docker.

---

## 📋 Test Methods

### 1. ⭐ Docker pytest (Recommended)
**19 comprehensive automated tests**

```bash
# All tests
docker-compose run --rm test

# Specific category
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# With coverage
docker-compose run --rm test pytest tests/test_api.py --cov=src
```

### 2. 🔧 Bash Script (Quick Manual)
**Fast integration testing**

```bash
cd backend
./test_api.sh /path/to/test.pdf
```

### 3. 📝 Manual curl
**Individual endpoint testing**

```bash
# See CURL_TESTS.md for complete list
curl http://localhost:8000/health | jq
```

---

## 📊 What Gets Tested

✅ Health check
✅ Document upload with page tracking
✅ Document list/get/delete
✅ Chat create/list/get/rename/delete
✅ Question answering with page citations
✅ Message persistence
✅ PDF file serving
✅ Error handling (404, 422)

---

## 🐛 Troubleshooting

### Tests fail
```bash
# Check backend is running
docker-compose ps

# View logs
docker-compose logs backend

# Restart services
docker-compose restart
```

### Need to rebuild
```bash
# After code changes
docker-compose build backend
docker-compose run --rm test
```

---

## 📚 More Info

- **DOCKER_TESTING.md** - Detailed Docker testing guide
- **TESTING_GUIDE.md** - Complete testing documentation
- **CURL_TESTS.md** - Manual curl commands
- **tests/README.md** - pytest documentation

---

## 💡 Pro Tips

```bash
# Run tests in background
docker-compose run -d test

# Interactive shell in test container
docker-compose run --rm test bash

# View test output with colors
docker-compose run --rm test pytest tests/test_api.py -v --color=yes
```

**Need help?** Check the troubleshooting sections in the docs above.
