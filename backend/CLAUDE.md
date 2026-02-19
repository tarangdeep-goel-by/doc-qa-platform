# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Backend Commands

```bash
# Rebuild after code changes
docker-compose build backend && docker-compose up -d --force-recreate backend

# Run all tests
docker-compose run --rm test

# Run specific test file/class/function
docker-compose run --rm test pytest tests/test_api.py -v
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# Unit tests only (fast, no external deps)
docker-compose run --rm unit-tests

# Integration tests (needs Qdrant)
docker-compose run --rm integration-tests

# API tests (needs backend + Qdrant)
docker-compose run --rm api-tests

# Run evals (always use -t for live output)
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/output.json \
  --label "description" --use-judge

# View eval history
docker exec doc-qa-backend python evaluation/view_history.py --detail --last 5
```

## Architecture

### App State — Lifespan Pattern

`api/main.py` initializes all components at startup via FastAPI lifespan, stored in `app.state`:

| State Key | Type | Purpose |
|-----------|------|---------|
| `embedder` | `Embedder` | Gemini embeddings |
| `vector_store` | `VectorStore` | Qdrant + BM25 hybrid search |
| `document_store` | `DocumentStore` | JSON-backed doc metadata |
| `chat_manager` | `ChatManager` | JSON-backed chat sessions |
| `qa_engine` | `QAEngine` | RAG orchestrator |
| `rag_config` | `RAGConfig` | Immutable pipeline config from env |
| `interaction_logger` | `InteractionLogger` | Append-only JSONL Q&A log |
| `feedback_store` | `FeedbackStore` | Append-only JSONL feedback |
| `user_store` | `UserStore \| None` | SQLite user DB (SaaS mode only, None in B2C) |

Routers access state via `request.app.state`.

### RAGConfig — Centralized Pipeline Config

`src/rag_config.py` is the **single source of truth** for all RAG pipeline parameters. Replaces manual env-var-to-function-param wiring that was error-prone.

```python
# At startup:
app.state.rag_config = RAGConfig.from_env()  # fast-fail on missing env vars

# In routers/eval:
result = qa_engine.answer_question(
    question=q,
    **rag_config.to_answer_kwargs(doc_ids=ids)
)
```

**Adding a new pipeline param**:
1. Add field to `RAGConfig` dataclass
2. Read from env in `from_env()`
3. It automatically flows to `answer_question()` via `to_answer_kwargs()`

### RAG Pipeline (qa_engine.py)

Two main methods:
- `answer_question()` — returns full result dict
- `answer_question_stream()` — yields SSE event dicts for streaming responses

Both accept the same kwargs (from `RAGConfig.to_answer_kwargs()`).

Pipeline stages:
1. Query decomposition (splits multi-part questions into sub-questions)
2. Query expansion (Gemini generates alternative phrasings)
3. Parallel search: vector (Qdrant) + BM25 keyword
4. RRF fusion (always on) + adaptive alpha weighting
5. Dynamic score cutoff (trims low-scoring chunks)
6. Cross-encoder reranking + position-aware blending
7. Context assembly → Gemini LLM → answer with citations

### Document Processing Pipeline

Upload flow (`api/routers/admin.py`):
1. File validation (size, MIME, magic bytes)
2. Save PDF to `data/uploads/{doc_id}.pdf`
3. Extract text (pdfplumber for tables, PyPDF2 fallback)
4. Chunk text (standard or semantic chunking)
5. Generate embeddings via Gemini
6. Store vectors + payloads in Qdrant
7. Rebuild BM25 index
8. Save metadata to `data/documents.json`

### Authentication (api/auth.py)

Dual-mode auth controlled by `JWT_SECRET` env var:

- **B2C** (`JWT_SECRET` empty): `get_current_user` returns `ANONYMOUS_USER` (admin role). All endpoints open.
- **SaaS** (`JWT_SECRET` set): Full JWT auth. `get_current_user` validates Bearer token. `require_admin` enforces admin-only.

Auth router (`api/routers/auth_router.py`) only registered when `AUTH_ENABLED=True`:
- `POST /api/auth/login` — returns access token, sets refresh cookie
- `POST /api/auth/refresh` — refresh via httponly cookie
- `GET /api/auth/me` — current user + feature flags
- `POST /api/auth/logout`

User store: `src/user_store.py` — SQLite-backed, bcrypt passwords, roles: `admin` | `client`.

Seed admin: `python -m scripts.seed_admin --email admin@example.com --password secret`

### Observability

- **InteractionLogger** (`src/interaction_logger.py`): Appends to `data/interactions.jsonl` on every Q&A. Records question, answer, sources, latency, RAG config.
- **FeedbackStore** (`src/feedback_store.py`): Appends to `data/feedback.jsonl` for thumbs up/down.
- Admin endpoints: `GET /api/admin/interactions`, `GET /api/admin/feedback`

### API Routers

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| `admin.py` | `/api/admin` | Upload, delete, bulk-delete documents, interactions, feedback |
| `query.py` | `/api/query` | Ask (non-chat), list documents |
| `chats.py` | `/api/chats` | CRUD chats, ask in chat (streaming SSE), message feedback, bulk-delete |
| `auth_router.py` | `/api/auth` | Login, refresh, me, logout (SaaS only) |

### Streaming (chats router)

`POST /api/chats/{chat_id}/ask` returns `StreamingResponse` with `text/event-stream`. Uses `qa_engine.answer_question_stream()` + async `event_generator()` pattern.

### BM25 Keyword Search

Persistent index (`src/bm25_index.py`): cached to `data/bm25/` as pickle. Rebuilds when documents change. Used in VectorStore for hybrid search alongside Qdrant vector search.

### Supporting Modules

- `src/gemini_retry.py` — Exponential backoff for Gemini 503/429
- `src/doc_router.py` — BM25-based automatic document routing (routes query to most relevant docs)
- `src/structure_detector.py` — Detects tables, lists, specs, section headers
- `src/semantic_chunker.py` — Alternative chunker (controlled by `USE_SEMANTIC_CHUNKING`)

## Evaluation Framework

```bash
# Standard eval with LLM judge
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/output.json --label "desc" --use-judge

# Fast eval (skip judge)
... --no-judge

# Feature ablation (one feature off at a time)
... --ablation

# Multi-turn conversational eval
... --conversational

# Generate dataset from PDF using Gemini oracle
docker exec -t doc-qa-backend python evaluation/generate_dataset.py \
  --pdf data/uploads/<doc_id>.pdf --output evaluation/datasets/out.json \
  --num-questions 30 --doc-name "Title"

# View/filter history
docker exec doc-qa-backend python evaluation/view_history.py --detail --last 5
docker exec doc-qa-backend python evaluation/view_history.py --dataset fx5u
```

Eval uses `RAGConfig.from_env()` — same single source of truth as the API.

## Environment Variables

All set in `docker-compose.yml` via `x-env-common` anchor. Fast-fail (`os.environ["KEY"]`) — missing vars raise KeyError immediately.

Required: `GEMINI_API_KEY`

Auth: `JWT_SECRET` (empty = B2C), `JWT_ACCESS_EXPIRY_MINUTES` (15), `JWT_REFRESH_EXPIRY_DAYS` (7), `CLIENT_DOCUMENT_VIEW` (feature flag)

See root `CLAUDE.md` for full RAG config table.
