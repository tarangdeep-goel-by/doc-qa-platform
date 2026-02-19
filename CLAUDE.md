# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Full-stack RAG (Retrieval Augmented Generation) platform for document Q&A. Upload PDFs, ask questions, get AI-powered answers with source citations. Supports two deployment modes: **B2C** (open access, no login) and **SaaS** (JWT auth, multi-user, role-based access).

**Stack**: React + TypeScript frontend, FastAPI backend, Qdrant vector DB, Google Gemini LLM

## Quick Start

```bash
# Start all services (Qdrant + backend)
docker-compose up -d

# Frontend development (separate terminal)
cd frontend && npm run dev

# Access points
# UI: http://localhost:3000
# API docs: http://localhost:8000/docs
# Qdrant: http://localhost:6333/dashboard
```

## Docker Development (Primary Workflow)

**No local Python env** — all backend code runs inside Docker container `doc-qa-backend`.

```bash
# Rebuild after code changes (container only mounts data/ and eval results, not code)
docker-compose build backend && docker-compose up -d --force-recreate backend

# Run tests
docker-compose run --rm test

# Run specific test
docker-compose run --rm test pytest tests/test_api.py::TestChats -v

# Run evals (always use -t for live progress output)
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/output.json \
  --label "description of changes"

# Generate eval dataset from any uploaded PDF
docker exec -t doc-qa-backend python evaluation/generate_dataset.py \
  --pdf data/uploads/<doc_id>.pdf \
  --output evaluation/datasets/my_dataset.json \
  --num-questions 30 --doc-name "My Document Title"

# View eval history
docker exec doc-qa-backend python evaluation/view_history.py --detail --last 5

# Check backend logs
docker-compose logs -f backend

# SaaS mode: seed admin user
docker exec doc-qa-backend python -m scripts.seed_admin \
  --email admin@example.com --password secret
```

**Critical gotchas**:
- `docker-compose restart` does NOT pick up rebuilt images. Always use `docker-compose up -d --force-recreate backend` after build.
- `docker exec` without `-t` buffers stdout until process exits — no live progress. Always use `-t` for evals.
- Volumes mounted: `backend/data/` and `backend/evaluation/results/` — code is baked into image.

## Authentication Modes

Controlled by `JWT_SECRET` env var in `docker-compose.yml`:

- **B2C mode** (default, `JWT_SECRET` empty): All endpoints open, no login. Anonymous user gets admin role.
- **SaaS mode** (`JWT_SECRET` set): JWT auth required. Roles: `admin` | `client`. Auth router registered at `/api/auth/`. User store in `data/users.db` (SQLite).

Auth dependency: `get_current_user` (returns `ANONYMOUS_USER` in B2C) and `require_admin` in `api/auth.py`.

## RAG Pipeline Architecture

```
Question
  ↓
Query Decomposition (optional, splits complex multi-part questions)
  ↓
Query Expansion (optional, generates alternative phrasings via Gemini)
  ↓
Parallel Search: [Vector/Semantic] + [BM25/Keyword]
  ↓
Fusion: RRF (always on) + Weighted (adaptive alpha auto-adjusts per query type)
  ↓
Dynamic Score Cutoff (trims low-scoring chunks post-retrieval)
  ↓
Cross-Encoder Reranking + Position-Aware Blending
  ↓
Context Assembly → Gemini LLM → Streamed Answer with Source Citations
```

### RAG Config — Single Source of Truth

`RAGConfig` dataclass (`src/rag_config.py`) reads all pipeline params from env vars at startup. **Never manually wire params** — use `rag_config.to_answer_kwargs()`:

```python
rag_config = RAGConfig.from_env()
result = qa_engine.answer_question(question=q, **rag_config.to_answer_kwargs(doc_ids=ids))
```

When adding a new pipeline param: add to `RAGConfig` dataclass + `from_env()` — it flows to all callers automatically.

### Environment Variables (docker-compose.yml)

| Variable | Value | Notes |
|----------|-------|-------|
| `GEMINI_MODEL` | `gemini-2.5-flash` | Main LLM |
| `GEMINI_FAST_MODEL` | `gemini-2.5-flash-lite` | Fast model for titles, expansion |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Changing requires Qdrant rebuild |
| `EMBEDDING_DIM` | `768` | Must match embedding model |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `2500` / `500` | Changing requires re-upload |
| `TOP_K_RESULTS` | `12` | Initial fetch; dynamic cutoff trims further |
| `USE_HYBRID_SEARCH` | `true` | BM25 + vector fusion |
| `USE_ADAPTIVE_ALPHA` | `true` | Auto-adjusts alpha per query type |
| `USE_RERANKING` | `true` | Cross-encoder reranking |
| `USE_QUERY_EXPANSION` | `true` | Generate alternative phrasings |
| `USE_QUERY_DECOMPOSITION` | `true` | Split multi-part questions |
| `USE_SEMANTIC_CHUNKING` | `false` | Alternative chunker |
| `JWT_SECRET` | `${JWT_SECRET:-}` | Empty = B2C, set = SaaS |

**Data-breaking changes**: Changing `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CHUNK_SIZE`, or `CHUNK_OVERLAP` requires `docker-compose down -v` + re-upload all documents.

## Evaluation Framework

- **Datasets**: JSON files in `evaluation/datasets/` — generate new ones with `generate_dataset.py`
- **Doc resolution**: Uses all doc_ids from `data/documents.json` (mirrors real user behavior)
- **History ledger**: `evaluation/results/history.jsonl` — append-only JSONL
- **Metrics**: LLM judge, semantic similarity, ROUGE-L, latency
- **CLI flags**: `--use-judge` (LLM scoring), `--no-judge` (fast, metrics only), `--ablation` (feature ablation), `--conversational` (multi-turn)

**Eval gotcha**: Pipeline params must flow through `RAGConfig` — check `to_answer_kwargs()`, not just config logging.

## Adding a New RAG Feature

1. Add env var to `docker-compose.yml` (in `x-env-common`)
2. Add field to `RAGConfig` dataclass + `from_env()` in `src/rag_config.py`
3. Implement in `src/qa_engine.py` or `src/vector_store.py`
4. Tests + rebuild + eval

## Persistent Data (`data/` directory)

```
data/
├── documents.json       # DocumentStore metadata
├── chats/{chat_id}.json # Chat sessions + messages
├── uploads/{doc_id}.pdf # Uploaded PDFs
├── bm25/                # BM25 index cache (pickle)
├── interactions.jsonl   # InteractionLogger (every Q&A logged)
├── feedback.jsonl       # FeedbackStore (thumbs up/down)
└── users.db             # SQLite user store (SaaS mode only)
```

## Detailed Guides

- **Frontend**: `frontend/CLAUDE.md` — dark glass design system, Zustand, auth components
- **Backend**: `backend/CLAUDE.md` — RAG pipeline, RAGConfig, streaming, testing, auth
- **Project status**: `PROJECT_STATUS.md` — recent changes, metrics, roadmap
