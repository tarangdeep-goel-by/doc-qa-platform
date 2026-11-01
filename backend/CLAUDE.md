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
  --label "description"   # judge runs by default; --no-judge skips it

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
1. Classify + expand: one `GEMINI_FAST_MODEL` call labels simple/complex, writes 2 paraphrases and (if complex) 2-4 sub-questions
2. Query decomposition: complex questions run each sub-question through the full pipeline, then a synthesis call
3. Per variant: vector (Qdrant, top 20) + BM25 (top 20), RRF fusion; variant scores summed, original weighted 2x
4. Adaptive alpha runs this search three times, but RRF ignores alpha, so it has no effect (see `docs/NOTES.md` B1)
5. Cross-encoder reranking + position-aware blending
6. Dedup, noise filter, dynamic score cutoff (3-15 chunks), structure boost, neighbour-chunk fetch
7. Context assembly → `GEMINI_FAST_MODEL` (gemini-2.5-flash-lite) → answer with `[Source N]` citations

`GEMINI_MODEL` (gemini-2.5-flash) is passed to `QAEngine` but not used for generation; only the eval judge and dataset generator use it.

### Document Processing Pipeline

Upload flow (`api/routers/admin.py`):
1. File validation (extension allow-list `.pdf .docx .html .htm .txt`, size, magic bytes; 409 on duplicate filename)
2. Save original to `data/uploads/{doc_id}.{ext}`
3. Extract text (PDF: pdfplumber when `USE_PDFPLUMBER=true`, tables appended as Markdown; PyPDF2 only when `USE_PDFPLUMBER` is off or pdfplumber isn't installed, with no per-file fallback if pdfplumber fails. DOCX ~3000-char pseudo-pages; HTML/TXT one page)
4. Chunk text (structure-aware by default, or semantic with `USE_SEMANTIC_CHUNKING=true`), prefix `[Document | Page | Section]` enriched text
5. Generate embeddings of the enriched text via Gemini
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

- **InteractionLogger** (`src/interaction_logger.py`): Appends to `data/interactions.jsonl` for each completed chat answer (`POST /api/chats/{id}/ask`); `/api/query/ask` is not logged. Records question, answer, sources, latency, RAG config.
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
# Standard eval (LLM judge is on by default; --use-judge is accepted but a no-op)
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/output.json --label "desc"

# Fast eval (skip judge)
... --no-judge

# Feature ablation (one feature off at a time; scores retrieval metrics only,
# which are zero because no dataset has expected_sources)
... --ablation

# Re-chunk and re-embed every stored upload into a fresh collection first
... --reingest

# Multi-turn conversational eval: no flag, auto-detected from the dataset format
... --dataset evaluation/datasets/conversational_multi_doc.json

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

All set in `docker-compose.yml` via `x-env-common` anchor. Core pipeline vars fast-fail (`os.environ["KEY"]`) — missing vars raise KeyError immediately. Some ops vars have code fallbacks: `GEMINI_FAST_MODEL`, `CORS_ORIGINS`, `COOKIE_SECURE`, `MAX_UPLOAD_SIZE_MB`, `UPLOAD_RATE_LIMIT` (not in compose; default `10/minute`), `USE_PDFPLUMBER` (code default `false`, compose sets `true`), `LOG_LEVEL`.

Required: `GEMINI_API_KEY`

Auth: `JWT_SECRET` (empty = B2C, otherwise min 32 chars), `JWT_ACCESS_EXPIRY_MINUTES` (15), `JWT_REFRESH_EXPIRY_DAYS` (7), `CLIENT_DOCUMENT_VIEW` (feature flag)

See root `CLAUDE.md` for full RAG config table.
