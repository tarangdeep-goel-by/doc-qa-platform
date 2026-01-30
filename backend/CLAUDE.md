# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Backend-Specific Commands

### Development

```bash
# Local development (requires Python 3.11+)
python run_api.py

# Docker development
docker-compose up -d backend
docker-compose logs -f backend

# Rebuild after code changes
docker-compose build backend
docker-compose restart backend
```

### Testing

```bash
# Run all tests (Docker - recommended)
docker-compose run --rm test

# Run specific test file
docker-compose run --rm test pytest tests/test_api.py -v

# Run specific test class/function
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# With coverage
docker-compose run --rm test pytest tests/ --cov=src --cov-report=html

# Quick integration tests (bash script)
./test_api.sh tests/fixtures/test.pdf

# Local testing (if Python env set up)
pytest tests/ -v
```

### Code Quality

```bash
# Format code (if using black/ruff)
black src/ api/ tests/
ruff check src/ api/ tests/

# Type checking (if using mypy)
mypy src/ api/
```

## Architecture Patterns

### Application State Management

FastAPI uses lifespan events to manage shared application state. Components are initialized once at startup and stored in `app.state`:

```python
# api/main.py - Initialization pattern
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize shared components
    embedder = Embedder(model_name=embedding_model)
    vector_store = VectorStore(host=qdrant_host, port=qdrant_port)
    document_store = DocumentStore(data_dir=data_dir)
    chat_manager = ChatManager(base_dir=data_dir)
    qa_engine = QAEngine(embedder, vector_store, gemini_api_key)

    # Store in app state
    app.state.embedder = embedder
    app.state.vector_store = vector_store
    # ... etc

    yield
    # Cleanup on shutdown
```

**Accessing components in routers:**

```python
# api/routers/admin.py
from fastapi import Request

def get_app_state(request: Request):
    return request.app.state

@router.post("/upload")
async def upload_document(request: Request):
    state = get_app_state(request)
    embedder = state.embedder
    vector_store = state.vector_store
    # Use components...
```

### RAG Pipeline Architecture

The system implements a multi-stage RAG pipeline with optional enhancements:

**Basic Pipeline** (src/qa_engine.py):
1. Embed question → 2. Vector search → 3. Build context → 4. Generate answer

**Enhanced Pipeline** (configurable via .env):
1. **Query Expansion** (`USE_QUERY_EXPANSION=true`): Generate alternative phrasings
2. **Hybrid Search** (`USE_HYBRID_SEARCH=true`): Combine semantic (vector) + keyword (BM25) search
3. **Reciprocal Rank Fusion** (`USE_RRF=true`): Merge results from multiple search strategies
4. **Reranking** (`USE_RERANKING=true`): Use cross-encoder to rerank candidates
5. **Position-Aware Blending** (`RERANKER_BLENDING=position_aware`): Weight top results higher

**Flow with all enhancements:**
```
Question
  ↓
Query Expansion (optional)
  ↓
Parallel Search: [Vector Search] + [BM25 Search]
  ↓
RRF Fusion (if USE_RRF=true) or Weighted Fusion
  ↓
Reranker (cross-encoder scoring)
  ↓
Position-Aware Blending
  ↓
Context Building + LLM Generation
```

### Authentication & Authorization

**JWT-based auth** (src/auth.py, api/routers/auth.py):
- Access tokens: 30min default (configurable)
- Refresh tokens: 7 days default
- Bcrypt password hashing
- User isolation: documents/chats tied to `user_id`

**User Store:**
- Simple JSON-based: `data/users.json`
- Schema: `{user_id: {id, email, hashed_password, is_active, created_at}}`

**Protected endpoints pattern:**
```python
from src.auth import verify_token, get_current_user

@router.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    # Filter data by user_id
```

### Document Processing Pipeline

**Upload flow** (api/routers/admin.py:upload_document):
1. File validation (size, MIME type, magic bytes)
2. Save to `data/uploads/{doc_id}.pdf`
3. Extract text + metadata (DocumentProcessor)
4. Chunk text (TextChunker)
5. Generate embeddings (Embedder)
6. Store vectors + payloads (VectorStore → Qdrant)
7. Build BM25 index if hybrid search enabled
8. Save document metadata (DocumentStore → JSON)

**Payload structure in Qdrant:**
```python
{
    "text": "chunk content...",
    "doc_id": "uuid",
    "doc_title": "document.pdf",
    "chunk_index": 0,
    "user_id": "user-uuid",  # For multi-tenancy
    "page_number": 5,         # Optional, from PyPDF2
    "metadata": {...}         # PDF metadata
}
```

### BM25 Keyword Search

**Persistent BM25 index** (src/bm25_index.py):
- Caches tokenized corpus to `data/bm25/` (pickle format)
- Rebuilds when documents change
- Uses rank-bm25 library

**Usage in VectorStore:**
```python
# Add document
vector_store.add_document_chunks(chunks, embeddings)
# Automatically triggers BM25 index rebuild if hybrid search enabled

# Search
results = vector_store.search(
    query_vector=embedding,
    query_text=question,  # For BM25
    use_hybrid=True,
    alpha=0.5  # 0=keyword only, 1=semantic only, 0.5=balanced
)
```

### Chat Management

**Chat sessions** (src/chat_manager.py):
- Stored in `data/chats/{user_id}/{chat_id}.json`
- Schema: `{id, user_id, title, created_at, updated_at, messages: []}`
- Messages: `{id, question, answer, sources, timestamp}`

**Automatic title generation:**
- Uses Gemini to generate concise title from first question
- Fallback: "Chat from {timestamp}"

### Error Handling

**Centralized error handler** (api/error_handlers.py):
```python
@app.add_exception_handler(Exception, generic_exception_handler)

# Returns structured JSON errors:
{
    "detail": "Error message",
    "type": "ValueError",
    "timestamp": "2024-01-30T10:00:00Z"
}
```

**Rate limiting** (slowapi):
- Configured per-endpoint
- Example: `@limiter.limit("10/hour")` for uploads

## Testing Architecture

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (base_url, test_pdf)
├── test_api.py              # Main API integration tests (20+ tests)
├── test_bm25_index.py       # BM25 keyword search unit tests
├── test_hybrid_search.py    # Hybrid search integration tests
├── test_query_expansion.py  # Query expansion unit tests
├── test_reranker.py         # Reranker unit tests
├── test_rag_pipeline_integration.py  # End-to-end RAG tests
├── test_qa_guardrails.py    # LLM guardrails (refuse off-topic questions)
├── test_deleted_documents.py  # Document deletion cleanup tests
└── fixtures/
    └── test.pdf             # Test PDF file
```

### Key Test Patterns

**Fixtures in conftest.py:**
```python
@pytest.fixture
def base_url():
    return "http://localhost:8000"

@pytest.fixture
def test_pdf():
    # Generate test PDF or use fixture
    return "tests/fixtures/test.pdf"

@pytest.fixture
def auth_headers(base_url):
    # Login and return auth headers
    return {"Authorization": f"Bearer {token}"}
```

**Integration test pattern:**
```python
def test_upload_and_query(base_url, test_pdf, auth_headers):
    # Upload
    response = requests.post(f"{base_url}/api/admin/upload",
                            files={"file": open(test_pdf, "rb")},
                            headers=auth_headers)
    assert response.status_code == 200
    doc_id = response.json()["doc_id"]

    # Query
    response = requests.post(f"{base_url}/api/query/ask",
                            json={"question": "test"},
                            headers=auth_headers)
    assert response.status_code == 200
    assert "answer" in response.json()
```

## Environment Configuration

### Critical Environment Variables

**Required:**
- `GEMINI_API_KEY`: Must be set

**Authentication:**
- `JWT_SECRET_KEY`: Change in production (256-bit secret)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Default 30
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Default 7

**Security:**
- `ALLOWED_ORIGINS`: CORS whitelist (comma-separated)
- `MAX_FILE_SIZE_MB`: Default 50
- `ALLOWED_MIME_TYPES`: Default "application/pdf"
- `RATE_LIMIT_ENABLED`: Default true
- `UPLOAD_RATE_LIMIT`: Default "10/hour"

**RAG Optimization Toggles:**
- `USE_HYBRID_SEARCH`: Enable BM25 + vector fusion (default true)
- `USE_RERANKING`: Enable cross-encoder reranking (default true)
- `USE_QUERY_EXPANSION`: Generate alternative phrasings (default false)
- `USE_RRF`: Use Reciprocal Rank Fusion (default true)

See `.env.example` for full list.

## Common Development Tasks

### Adding a New Endpoint

1. Define Pydantic schemas in `api/schemas.py`
2. Add endpoint to appropriate router (`admin.py`, `query.py`, `chats.py`)
3. Access app state via `get_app_state(request)`
4. Add test in `tests/test_api.py`
5. Run tests: `docker-compose run --rm test`

### Adding a New RAG Feature

1. Add configuration to `.env.example`
2. Implement logic in `src/qa_engine.py` or `src/vector_store.py`
3. Add unit tests in `tests/`
4. Add integration test in `tests/test_rag_pipeline_integration.py`
5. Update docstrings and comments

### Debugging RAG Results

```python
# Add logging to qa_engine.py
import logging
logger = logging.getLogger(__name__)

def answer_question(self, question: str, ...):
    logger.info(f"Query: {question}")

    # Log retrieved chunks
    logger.info(f"Retrieved {len(results)} chunks")
    for result in results:
        logger.info(f"Score: {result.score}, Text: {result.payload['text'][:100]}")

    # Log final prompt
    logger.info(f"Prompt: {prompt}")
```

Check logs:
```bash
docker-compose logs backend | grep "Query:"
```

### Modifying Chunking Strategy

1. Update `src/chunker.py` - modify `split_text()` method
2. Update `.env` - `CHUNK_SIZE`, `CHUNK_OVERLAP`
3. **Important:** Re-upload all documents (chunks change)
4. Run tests to verify: `docker-compose run --rm test`

### Switching Embedding Models

1. Update `.env`:
   ```env
   EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
   EMBEDDING_DIM=768  # Must match model dimension
   ```
2. **Important:** Recreate Qdrant collection (dimension must match):
   ```bash
   docker-compose down -v  # Deletes Qdrant data
   docker-compose up -d
   ```
3. Re-upload all documents

### Adding Multi-Tenancy Filtering

Pattern used throughout the codebase:

```python
# Filtering by user_id in VectorStore
def search(self, query_vector, user_id=None, doc_ids=None):
    must_conditions = []

    if user_id:
        must_conditions.append(
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        )

    if doc_ids:
        must_conditions.append(
            FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))
        )

    query_filter = Filter(must=must_conditions) if must_conditions else None
    # ... search with filter
```

## Performance Considerations

**Bottlenecks:**
1. **Document upload:** 10-30s for 200-page book (embedding generation)
2. **Query latency:** 2-3s (50ms embedding + 50ms search + 1-2s LLM)
3. **Reranking:** Adds ~200ms for 10 candidates

**Optimization opportunities:**
- Use GPU for embeddings (torch.cuda)
- Cache frequent queries (Redis)
- Async document processing (Celery/RQ)
- Batch reranking

## Migration Notes

### From JSON to PostgreSQL (Future)

Current state stores are JSON-based:
- `data/documents.json` (DocumentStore)
- `data/users.json` (UserStore)
- `data/chats/{user_id}/{chat_id}.json` (ChatManager)

To migrate:
1. Add SQLAlchemy models (`src/database.py`)
2. Create migration script
3. Replace store methods with DB queries
4. Keep Qdrant for vectors (no change)

### From Synchronous to Async Processing

Current upload is blocking (~30s). To add async:
1. Add task queue (Celery/RQ + Redis)
2. Return `task_id` immediately on upload
3. Add `GET /api/admin/tasks/{task_id}` status endpoint
4. Poll from frontend until complete

## Troubleshooting

**"Connection to Qdrant failed":**
```bash
docker ps | grep qdrant
docker logs doc-qa-qdrant
docker-compose restart qdrant
```

**"No text extracted from PDF":**
- PDF may be image-based (needs OCR)
- Try different library (pdfplumber, PyMuPDF)

**"Tests failing":**
```bash
docker-compose ps  # Check all services running
docker-compose logs backend  # Check backend logs
docker-compose restart  # Restart all services
docker-compose down && docker-compose up -d  # Full restart
```

**"Low relevance scores":**
- Check if question is too vague
- Try query expansion: `USE_QUERY_EXPANSION=true`
- Check chunk size (may be too large/small)
- Inspect retrieved chunks in response `sources`
