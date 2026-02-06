# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information

**GitHub Repository**: https://github.com/<your-username>/doc-qa-platform
**Owner**: tarangdeep-goel-by

## What This Is

Full-stack RAG (Retrieval Augmented Generation) platform for document Q&A. Upload PDFs, ask questions, get AI-powered answers with source citations.

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

## Project Structure

```
doc-qa-platform/
├── frontend/                # React + TypeScript + Zustand + Tailwind
│   └── CLAUDE.md            # Frontend architecture & patterns
├── backend/
│   ├── api/                 # FastAPI routers (admin, query, chats)
│   │   └── schemas.py       # Pydantic models
│   ├── src/                 # Core pipeline
│   │   ├── qa_engine.py     # RAG orchestrator (search → rerank → generate)
│   │   ├── vector_store.py  # Qdrant + BM25 hybrid search
│   │   ├── document_processor.py  # PDF extraction (PyPDF2 + pdfplumber)
│   │   ├── embedder.py      # Gemini embeddings
│   │   ├── chunker.py       # Text chunking with overlap
│   │   ├── bm25_index.py    # Persistent BM25 keyword index
│   │   └── chat_manager.py  # Chat session persistence (JSON files)
│   ├── evaluation/          # Eval framework
│   │   ├── run_evaluation.py      # Main eval harness
│   │   ├── view_history.py        # CLI history viewer
│   │   ├── backfill_history.py    # One-time ledger backfill
│   │   ├── datasets/              # Benchmark question sets (JSON)
│   │   └── results/               # Eval outputs + history.jsonl ledger
│   ├── tests/               # 136 pytest tests
│   └── CLAUDE.md            # Backend architecture & patterns
├── docker-compose.yml       # Qdrant + backend + test services
└── PROJECT_STATUS.md        # Current state, recent changes, roadmap
```

## Docker Development (Primary Workflow)

**No local Python env** — all backend code runs inside Docker container `doc-qa-backend`.

```bash
# Rebuild after code changes (container only mounts data/, not code)
docker-compose build backend && docker-compose up -d --force-recreate backend

# Run tests
docker-compose run --rm test

# Run evals (always use -t for live progress output)
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/output.json \
  --label "description of changes"

# View eval history
docker exec doc-qa-backend python evaluation/view_history.py --detail --last 5

# Check backend logs
docker-compose logs -f backend
```

**Critical gotcha**: `docker-compose restart` does NOT pick up rebuilt images. Always use `docker-compose up -d --force-recreate backend` after `docker-compose build backend`.

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
Fusion: RRF (Reciprocal Rank Fusion) or Weighted (adaptive alpha)
  ↓
Dynamic Score Cutoff (step 2.8 — trims low-scoring chunks post-retrieval)
  ↓
Cross-Encoder Reranking + Position-Aware Blending
  ↓
Context Assembly → Gemini LLM → Answer with Source Citations
```

### RAG Config (Environment Variables)

All set in `docker-compose.yml`, read by backend at startup:

| Variable | Current Value | Notes |
|----------|--------------|-------|
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Changing requires Qdrant collection rebuild |
| `EMBEDDING_DIM` | `768` | Must match embedding model |
| `CHUNK_SIZE` | `2500` | Changing requires re-uploading all documents |
| `CHUNK_OVERLAP` | `500` | Changing requires re-uploading all documents |
| `TOP_K_RESULTS` | `12` | Initial fetch count; dynamic cutoff trims further |
| `USE_HYBRID_SEARCH` | `true` | BM25 + vector fusion |
| `HYBRID_ALPHA` | `0.5` | 0=keyword only, 1=semantic only |
| `USE_ADAPTIVE_ALPHA` | `true` | Auto-adjusts alpha per query type |
| `USE_RERANKING` | `true` | Cross-encoder reranking |
| `RERANKER_BLENDING` | `position_aware` | Weight top results higher |
| `USE_RRF` | `true` | Reciprocal Rank Fusion |
| `USE_QUERY_EXPANSION` | `false` | Currently off (adds latency) |
| `USE_QUERY_DECOMPOSITION` | `true` | Splits multi-part questions |
| `USE_PDFPLUMBER` | `true` | Table-aware PDF extraction |

**Data-breaking changes**: Changing `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CHUNK_SIZE`, or `CHUNK_OVERLAP` requires:
1. `docker-compose down -v` (deletes Qdrant data)
2. `docker-compose up -d`
3. Re-upload all documents

## Evaluation Framework

### Running Evals

```bash
# Multi-doc benchmark (77 questions, ~20 min)
docker exec -t doc-qa-backend python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/real_world_multi_doc.json \
  --output evaluation/results/multi_doc_eval.json \
  --label "description" --use-judge

# View history (39+ runs tracked)
docker exec doc-qa-backend python evaluation/view_history.py --detail --last 5

# Filter by dataset
docker exec doc-qa-backend python evaluation/view_history.py --dataset fx5u
```

### Eval Architecture

- **Datasets**: JSON files in `evaluation/datasets/` with questions + expected answers
- **Doc resolution**: Eval uses all doc_ids from `data/documents.json` (mirrors real user behavior)
- **History ledger**: `evaluation/results/history.jsonl` — append-only JSONL, one line per run
- **Metrics**: LLM judge (accuracy, completeness, organization, relevance), semantic similarity, ROUGE-L, latency
- **Current best**: 4.72/5 overall on 77-question multi-doc benchmark

### Eval Gotchas

- Pipeline params (`use_query_decomposition`, `use_adaptive_alpha`) must be explicitly passed to `qa_engine.answer_question()` — easy to miss when adding new params
- Env vars use fast-fail (`os.environ["KEY"]`) — missing vars raise KeyError immediately, no silent defaults
- Always use `docker exec -t` (not `docker exec`) for live progress — without `-t`, stdout buffers until process exits

## Testing

```bash
# All tests (136 tests, needs backend + Qdrant running)
docker-compose run --rm test

# Unit tests only (fast)
docker-compose run --rm unit-tests

# Integration tests (needs Qdrant)
docker-compose run --rm integration-tests

# API tests (needs backend + Qdrant)
docker-compose run --rm api-tests

# Specific test file
docker-compose run --rm test pytest tests/test_api.py -v
```

## Key Design Decisions

- **Zustand** for frontend state — minimal boilerplate, no providers
- **Qdrant** for vectors — self-hosted, production-ready
- **Gemini** for LLM + embeddings — large context window, fast, cheap
- **Hybrid search** — semantic + keyword (BM25) for better recall
- **JSON file storage** for chats/docs — simple, no DB migration needed yet
- **pdfplumber** for PDF extraction — handles tables better than PyPDF2 (still available as fallback)

## Common Tasks

### Adding a New RAG Feature

1. Add env var to `docker-compose.yml` (all services that need it)
2. Implement in `backend/src/qa_engine.py` or `backend/src/vector_store.py`
3. Wire through in `backend/api/routers/query.py` AND `backend/api/routers/chats.py`
4. Wire through in `backend/evaluation/run_evaluation.py` (fast-fail env read + pass to answer_question)
5. Add tests
6. Rebuild container and run eval

### Debugging RAG Quality

1. Run eval with `--use-judge` flag
2. Check per-question scores in output JSON
3. Look at `sources` in responses — are the right chunks being retrieved?
4. Check if question type maps to the right search strategy (adaptive alpha)
5. Compare against history: `view_history.py --detail --last 10`

## Detailed Guides

- **Frontend**: `frontend/CLAUDE.md` — components, Zustand, design system, API client
- **Backend**: `backend/CLAUDE.md` — RAG pipeline, testing, env config, error handling
- **Project status**: `PROJECT_STATUS.md` — recent changes, metrics, roadmap

## Troubleshooting

**Container has stale code**: Rebuild and force-recreate (restart alone doesn't work):
```bash
docker-compose build backend && docker-compose up -d --force-recreate backend
```

**Eval shows wrong scores**: Check that all pipeline params are wired through to `qa_engine.answer_question()` in `run_evaluation.py`. Config dict logging can look correct while the actual function call misses params.

**No live output from docker exec**: Use `docker exec -t` (allocate pseudo-TTY).

**Qdrant connection failed**: `docker-compose restart qdrant` or full `docker-compose down && docker-compose up -d`.

**Frontend can't reach API**: Check backend is running at http://localhost:8000/health, check proxy in `frontend/vite.config.ts`.
