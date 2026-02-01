# Project Status - Document Q&A Platform

**Last Updated**: February 1, 2026

This document tracks implementation progress, recent changes, and next steps for the Document Q&A Platform.

---

## 🎯 Current Status: Evaluation-Driven RAG Quality Improvements

The platform is fully functional with an automated evaluation framework measuring answer quality against Claude.ai gold-standard answers. Systematic improvements (Gemini embeddings, enhanced BM25, chunk deduplication) have pushed semantic similarity from 0.742 to 0.897 (+21%).

---

## ✅ Completed Features

### Core Infrastructure
- [x] FastAPI backend with proper project structure
- [x] Docker Compose setup for Qdrant vector database
- [x] Environment configuration (.env)
- [x] API documentation (Swagger/OpenAPI at `/docs`)
- [x] Health check endpoint

### Document Processing Pipeline
- [x] PDF upload via API endpoint
- [x] Text extraction using PyPDF2
- [x] Smart text chunking (2500 chars, 500 overlap)
- [x] Sentence-boundary aware chunking
- [x] Gemini embedding generation (gemini-embedding-001, 768-dim, MTEB 71.5%)
- [x] Vector storage in Qdrant
- [x] Document metadata management (JSON store)

### Query & Retrieval (RAG)
- [x] Question embedding
- [x] Semantic search in Qdrant
- [x] Context retrieval with relevance scores
- [x] Answer generation using Google Gemini 2.0 Flash
- [x] Source citation in responses
- [x] Document filtering (search specific docs or all docs)
- [x] Hybrid search (vector + BM25 keyword search)
- [x] **Query Expansion** - Generate alternative query phrasings (15-25% recall improvement) ✨
- [x] **Reciprocal Rank Fusion (RRF)** - More robust hybrid search score fusion ✨
- [x] Reranking with cross-encoder
- [x] **Position-Aware Reranker Blending** - Context-aware score blending ✨
- [x] Configurable relevance thresholds (min_score)
- [x] **Chunk deduplication** - Jaccard similarity-based removal of near-duplicate chunks ✨

### Evaluation Framework ✨ NEW
- [x] Automated benchmark evaluation (`evaluation/run_evaluation.py`)
- [x] Upload-and-eval one-command script (`scripts/upload_and_eval.py`)
- [x] Benchmark dataset format with gold-standard Q&A pairs
- [x] Metrics: semantic similarity, ROUGE-L, ROUGE-1, NDCG@k, MRR
- [x] Console + HTML reporters with experiment comparison
- [x] Re-chunking migration script (`scripts/rechunk_documents.py`)

### Multi-Chat System
- [x] Create named chat sessions
- [x] Associate documents with chats
- [x] Chat message persistence
- [x] Gemini conversation history tracking
- [x] Rename and delete chats
- [x] List all chats with metadata
- [x] **Deleted document handling** ✨
- [x] Soft delete pattern (preserve history)
- [x] Automatic filtering of unavailable documents

### Admin Endpoints
- [x] `POST /api/admin/upload` - Upload documents
- [x] `GET /api/admin/documents` - List all documents
- [x] `GET /api/admin/documents/{doc_id}` - Get document details
- [x] `GET /api/admin/documents/{doc_id}/file` - Download/view PDF
- [x] `DELETE /api/admin/documents/{doc_id}` - Delete documents

### Chat Endpoints
- [x] `POST /api/chats` - Create new chat
- [x] `GET /api/chats` - List all chats
- [x] `GET /api/chats/{chat_id}` - Get chat with messages
- [x] `POST /api/chats/{chat_id}/ask` - Ask question in chat context
- [x] `PUT /api/chats/{chat_id}/rename` - Rename chat
- [x] `DELETE /api/chats/{chat_id}` - Delete chat

### Query Endpoints
- [x] `POST /api/query/ask` - Ask questions with optional document filtering
- [x] `GET /api/query/documents` - List available documents

---

## 🆕 Recent Changes (February 1, 2026)

### Evaluation Framework & RAG Quality Improvements

**What was implemented:**
Built an automated evaluation framework and applied systematic improvements to close the quality gap with Claude.ai answers.

**Evaluation Framework:**
- `backend/evaluation/` - Full eval suite with metrics, reporters, benchmark datasets
- `backend/scripts/upload_and_eval.py` - One-command upload + eval + report
- `backend/evaluation/datasets/fx5u_qa_benchmark.json` - 4 gold-standard Q&A pairs
- Metrics: semantic similarity, ROUGE-L/1, NDCG@k, MRR, latency

**RAG Improvements Applied (measured via eval):**

| Change | Semantic Sim | Notes |
|--------|-------------|-------|
| Baseline (MiniLM, reranking off) | 0.742 | Starting point |
| + Enable reranking + fix confidence bug | 0.779 (+5%) | Cross-encoder scores can be negative; fixed min_score check |
| + Gemini embeddings (768-dim) | 0.893 (+15%) | Replaced all-MiniLM-L6-v2 (MTEB 56) with gemini-embedding-001 (MTEB 71.5%) |
| + Enhanced BM25 + chunk dedup | 0.897 (+21% total) | Stop words, regex tokenizer, Jaccard deduplication |

**Files Created:**
- `backend/evaluation/__init__.py`, `benchmark_dataset.py`, `run_evaluation.py`
- `backend/evaluation/metrics/` - `retrieval.py`, `answer_quality.py`, `performance.py`
- `backend/evaluation/reporters/` - `console_reporter.py`, `html_reporter.py`
- `backend/evaluation/datasets/fx5u_qa_benchmark.json`
- `backend/scripts/upload_and_eval.py`
- `backend/evaluation/results/` - baseline, reranking_fixed, gemini_embeddings, bm25_dedup JSONs

**Files Modified:**
- `backend/src/embedder.py` - Dual-mode: Gemini API or local sentence-transformers
- `backend/src/qa_engine.py` - Confidence threshold fix for reranked scores, chunk deduplication
- `backend/src/bm25_index.py` - Regex tokenizer, stop word removal
- `backend/api/main.py` - Pass Gemini params to Embedder
- `docker-compose.yml` - Switched to gemini-embedding-001 (768-dim), enabled reranking
- `backend/.env.example` - Updated embedding defaults

**Key Bug Fix:**
Cross-encoder reranking produces scores in range -10 to +10. Position-aware blending can yield negative blended scores. The `MIN_CONFIDENCE_SCORE=0.3` threshold was rejecting valid reranked results, causing "I don't have enough information" responses. Fixed by skipping the threshold when reranking is active.

---

## 🆕 Recent Changes (January 31, 2026)

### Document Chat Count Feature Tests

**What was implemented:**
Added comprehensive test coverage for the document chat count feature in `/api/query/documents` endpoint.

**New Test Class: TestQueryDocuments**
Created 5 test cases covering all edge cases:

1. **test_query_documents_basic** - Validates endpoint returns correct structure
   - Verifies all fields present: doc_id, title, chat_count, chats, etc.
   - Confirms data types are correct

2. **test_query_documents_no_chats** - Document with no associated chats
   - Verifies chat_count = 0
   - Verifies chats = []

3. **test_query_documents_single_chat** - Document used in exactly 1 chat
   - Verifies chat_count = 1
   - Verifies chat details (id, name) are correct

4. **test_query_documents_multiple_chats** - Document used in 3 chats
   - Verifies chat_count = 3
   - Verifies all chat IDs present in response

5. **test_query_documents_mixed_usage** - Multiple documents with different usage
   - Document A in chats 1 and 3 → chat_count = 2
   - Document B in chats 2 and 3 → chat_count = 2
   - Verifies selective counting per document

**Files Modified:**
- `backend/tests/test_api.py` - Added TestQueryDocuments class with 5 tests (+208 lines)

**Test Results:**
- All 24 API integration tests passing ✅
- Total test suite: 136 tests (131 → 136, +5 new tests)

**Benefits:**
- Complete test coverage for document-chat relationship tracking
- Validates feature works across all usage patterns
- Ensures no regressions in future changes
- Follows existing test patterns (fixtures, cleanup, assertions)

---

## 🆕 Recent Changes (January 29, 2026)

### QMD-Inspired RAG Optimizations (Latest) ⭐

**What was implemented:**
Adopted three advanced retrieval techniques from QMD (Query-based Multi-modal Document understanding) to significantly improve answer quality:

1. **Query Expansion** - LLM generates 2 alternative phrasings of each question
   - Original query weighted 2×, variants weighted 1× each
   - Results from all queries fused together
   - **Expected improvement:** +15-25% recall
   - Configurable via `USE_QUERY_EXPANSION` and `QUERY_EXPANSION_VARIANTS`

2. **Reciprocal Rank Fusion (RRF)** - More robust hybrid search
   - Replaces weighted score averaging with position-based fusion
   - Formula: `score = Σ 1/(k + rank)` where k=60
   - Includes position bonuses for top-3 results
   - **Expected improvement:** +5-10% ranking quality
   - Configurable via `USE_RRF` and `RRF_K_PARAMETER`

3. **Position-Aware Reranker Blending** - Context-sensitive score fusion
   - Top 3 chunks: 75% retrieval weight, 25% reranker
   - Ranks 4-10: 50/50 blend
   - Ranks 11+: 25% retrieval, 75% reranker
   - Preserves good initial rankings while improving lower ranks
   - **Expected improvement:** +3-5% top-k precision
   - Configurable via `RERANKER_BLENDING` (position_aware/replace)

**Files Modified:**
1. `backend/src/qa_engine.py` - Added `_expand_query()`, updated `answer_question()` with new params
2. `backend/src/vector_store.py` - Added `multi_query_hybrid_search()`, `_reciprocal_rank_fusion()`
3. `backend/src/reranker.py` - Added `rerank_with_position_blending()`
4. `backend/api/routers/query.py` - Environment-based config defaults, new API params
5. `backend/api/schemas.py` - Extended `QueryRequest` with advanced options
6. `backend/.env.example` - Added configuration for all new features

**Files Created:**
1. `backend/tests/test_query_expansion.py` - 10 comprehensive tests
2. Updated `backend/tests/test_hybrid_search.py` - Added 5 RRF tests
3. Updated `backend/tests/test_reranker.py` - Added 9 position-aware blending tests

**Configuration (.env):**
```bash
# Query Expansion
USE_QUERY_EXPANSION=false  # Set true to enable (adds ~1-2s latency)
QUERY_EXPANSION_VARIANTS=2
QUERY_EXPANSION_WEIGHT=2.0

# Reciprocal Rank Fusion
USE_RRF=true  # Enabled by default
RRF_K_PARAMETER=60
RRF_TOP_BONUSES=0.05,0.02,0.02

# Position-Aware Reranking
RERANKER_BLENDING=position_aware  # or "replace" for standard reranking
```

**API Usage:**
```bash
# Basic query (uses env defaults)
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?"}'

# Advanced query with all options
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "use_query_expansion": true,
    "use_rrf": true,
    "rerank_blending": "position_aware"
  }'
```

**Expected Overall Impact:**
- Recall: +15-25% (query expansion)
- Ranking quality: +5-10% (RRF)
- Top-k precision: +3-5% (position-aware blending)
- **Total answer quality improvement: ~20-30%**

**Trade-offs:**
- Query expansion adds 1-2s latency (LLM call for variants)
- RRF and position-aware blending have negligible overhead
- All features are optional and configurable

---

## 🆕 Recent Changes (January 22, 2026)

### Deleted Document Handling

**What was implemented:**
- Fixed handling of deleted documents in chat contexts
- Chats now maintain doc_id references even after deletion (soft delete pattern)
- RAG pipeline automatically filters out deleted documents
- Clear user-facing error messages when documents are unavailable
- Fixed QA engine sources format inconsistency

**Files Modified:**
1. `backend/api/routers/chats.py` - Filter deleted docs before RAG, return clear messages
2. `backend/api/routers/query.py` - Validate doc_ids in legacy endpoint
3. `backend/api/routers/admin.py` - Soft delete (keep doc_ids in chats for history)
4. `backend/src/qa_engine.py` - Fixed sources format for low-confidence responses
5. `backend/tests/test_deleted_documents.py` - Updated test expectations

**Behavior:**
```bash
# Delete document
DELETE /api/admin/documents/{doc_id}
# Response: "Document 'test.pdf' deleted successfully. 2 chat(s) reference this document"

# Ask in chat with deleted docs
POST /api/chats/{chat_id}/ask
{
  "question": "What is this about?"
}
# Response: "I cannot answer questions for this chat because all associated
#            documents have been deleted. Please add new documents to continue."

# Chat with mixed documents (some deleted)
# Uses only available documents automatically
```

**Benefits:**
- Chat history preserved (audit trail of what docs were used)
- No confusing "no information found" errors
- Automatic filtering prevents RAG pipeline errors
- Frontend can show "X documents deleted" warnings

**Test Coverage:**
- All 107 tests passing ✅
- Comprehensive deleted document test suite
- Integration tests for RAG pipeline with deleted docs

---

## 🆕 Recent Changes (January 21, 2026)

### Document Filtering Feature

**What was implemented:**
- Added optional `doc_ids: List[str]` parameter to query API
- Users can now search within specific documents or across all documents
- Supports single or multiple document filtering

**Files Modified:**
1. `backend/api/schemas.py` - Added `doc_ids` field to `QueryRequest`
2. `backend/src/vector_store.py` - Added `MatchAny` filter support
3. `backend/src/qa_engine.py` - Updated `answer_question()` to accept `doc_ids`
4. `backend/api/routers/query.py` - Pass `doc_ids` from request to QA engine

**Benefits:**
- Prevents cross-contamination from irrelevant documents
- Improves relevance scores when user knows which doc has the answer
- Maintains backward compatibility (no filter = search all)

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Upload Pipeline:                                                    │
│  PDF → Extract → Chunk → Embed → Qdrant + BM25 + Metadata Store    │
│                                                                       │
│  Enhanced Query Pipeline (RAG):                                      │
│  Question → Query Expansion (LLM) → Multi-Query Embed →             │
│  Hybrid Search (Vector + BM25 with RRF) → Rerank (Cross-Encoder    │
│  with Position-Aware Blending) → Generate (Gemini) →                │
│  Answer + Sources                                                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
         ↓                                    ↓
    ┌─────────┐                          ┌─────────┐
    │ Qdrant  │                          │ Gemini  │
    │ Vectors │                          │   API   │
    │  +BM25  │                          │(Gen+QE) │
    └─────────┘                          └─────────┘
```

---

## 🔧 Technical Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend Framework | FastAPI | Async, auto-docs, type hints |
| Vector Database | Qdrant | Self-hosted via Docker |
| Embeddings | Gemini Embedding API | gemini-embedding-001 (768-dim, MTEB 71.5%) |
| Keyword Search | BM25 (rank-bm25) | Stop words, regex tokenizer, cached to disk |
| Reranker | CrossEncoder | ms-marco-MiniLM-L-6-v2 |
| LLM | Google Gemini 2.5 Flash | Generation + Query Expansion |
| Document Processing | PyPDF2 | PDF-only currently |
| Metadata Store | JSON file | Simple file-based storage |
| Retrieval Strategy | Hybrid + RRF | Vector + BM25 with Reciprocal Rank Fusion |
| Score Optimization | Position-Aware | Context-sensitive reranker blending |

---

## 📈 Performance Metrics

### Baseline Performance
- **Upload**: ~10-30s for 200-page book
- **Query (Standard)**: ~2-3s total (embed + search + generate)
- **Embedding**: ~50ms per chunk (CPU)
- **Vector Search**: <100ms even with large collections
- **BM25 Search**: ~50ms with cached index

### Enhanced RAG Performance
- **Query (with Query Expansion)**: ~3-5s total (+1-2s for LLM expansion)
- **RRF Fusion**: <10ms additional overhead (negligible)
- **Position-Aware Reranking**: <5ms additional overhead (negligible)
- **Hybrid Search**: ~100-150ms (vector + BM25 + fusion)

### Quality Improvements (Measured via Eval Framework)
- **Semantic Similarity vs Claude.ai**: 0.897 avg (baseline was 0.742, +21%)
- **ROUGE-L**: 0.152 avg
- **Best question (q1)**: 0.932 similarity
- **Weakest question (q3)**: 0.877 similarity

---

## 🚧 Known Limitations

1. **PDF-only**: No support for DOCX, HTML, TXT yet
2. **No authentication**: Open API endpoints
3. **Synchronous uploads**: User waits for processing to complete
4. **JSON metadata store**: Not suitable for high concurrency
5. **No frontend UI**: API-only currently

---

## 📝 Next Steps (Prioritized)

### Phase 1: Additional Document Formats (High Priority)
- [ ] Add DOCX support (python-docx)
- [ ] Add HTML support (BeautifulSoup4)
- [ ] Add plain TXT support
- [ ] Unified document processor interface

**Estimated Effort**: 4-6 hours

### Phase 2: Frontend UI (High Priority)
- [ ] React + TypeScript setup
- [ ] Document upload interface (drag-drop)
- [ ] Document list view with filters
- [ ] Q&A chat interface
- [ ] Document selector dropdown for filtered search
- [ ] Source highlighting/navigation

**Estimated Effort**: 2-3 days

### Phase 3: Enhanced Search Features ✅ MOSTLY COMPLETE
- [x] Hybrid search (semantic + keyword) - **DONE**
- [x] Query expansion for improved recall - **DONE**
- [x] Advanced reranking with position-aware blending - **DONE**
- [x] Reciprocal Rank Fusion for robust score fusion - **DONE**
- [x] Configurable chunk retrieval (user sets top_k per query) - **DONE**
- [ ] Search history tracking
- [ ] Save/export Q&A sessions
- [ ] Advanced metadata filtering (date, type, tags)

**Estimated Effort**: Remaining items ~4-6 hours

### Phase 4: Production Readiness (Medium Priority)
- [ ] User authentication (JWT)
- [ ] PostgreSQL for metadata (replace JSON store)
- [ ] Redis caching for frequent queries
- [ ] Async document processing with status polling
- [ ] Rate limiting
- [ ] Structured logging (JSON logs)
- [ ] Health checks for all dependencies
- [ ] Prometheus metrics

**Estimated Effort**: 3-4 days

### Phase 5: Advanced Features (Low Priority)
- [ ] Document versioning
- [ ] Multi-user support with permissions
- [ ] Document collections/folders
- [ ] Collaborative Q&A (shared sessions)
- [ ] Export to markdown/PDF
- [ ] LLM response streaming
- [ ] Support for multiple embedding models
- [ ] GPU acceleration for embeddings

**Estimated Effort**: 1-2 weeks

---

## 🧪 Testing Status

**Test Suite: 136 tests, all passing ✅**

### API Tests (24 tests)
- [x] Health check endpoint
- [x] Document upload, list, get, delete
- [x] Chat creation, listing, retrieval
- [x] Chat rename and deletion
- [x] Ask questions in chat context
- [x] Message persistence
- [x] Legacy query endpoint
- [x] Document chat count feature (5 tests) - **NEW** ✨

### Feature Tests
- [x] BM25 index (17 tests)
- [x] Hybrid search with RRF (18 tests) - **+5 new tests** ✨
- [x] QA guardrails (14 tests)
- [x] RAG pipeline integration (16 tests)
- [x] Reranker with position-aware blending (23 tests) - **+9 new tests** ✨
- [x] Deleted documents handling (14 tests)
- [x] Query expansion (10 tests) - **NEW** ✨

### Coverage
- [x] All API endpoints tested
- [x] Success cases (200, 201)
- [x] Error cases (400, 404, 422, 500)
- [x] Data persistence verified
- [x] Edge cases (empty queries, deleted docs, etc.)

### Manual Testing
- [x] Document upload via curl/Postman
- [x] Query endpoint with filtering
- [x] Chat workflows
- [x] PDF viewing in browser
- [ ] Load testing for concurrent queries
- [ ] Performance benchmarking

---

## 📚 Documentation

- [x] README.md - User-facing setup guide
- [x] CLAUDE.md - Developer guide for Claude Code
- [x] PROJECT_STATUS.md - This file
- [x] API documentation (auto-generated at `/docs`)
- [ ] Architecture diagrams
- [ ] Deployment guide (production)
- [ ] Contributing guidelines

---

## 🐛 Known Issues

None currently! 🎉

**Recently Fixed:**
- ✅ RRF score normalization (Jan 29) - Fixed min_score threshold compatibility
- ✅ Deleted documents breaking chat queries (Jan 22)
- ✅ QA engine sources format inconsistency (Jan 22)

---

## 💡 Ideas for Future Exploration

1. **Multi-modal RAG**: Support images, tables from PDFs
2. **Adaptive chunking**: Vary chunk size based on document structure
3. ~~**Re-ranking**: Add cross-encoder re-ranker~~ ✅ **IMPLEMENTED** (with position-aware blending)
4. ~~**Query expansion**: Generate multiple question variants~~ ✅ **IMPLEMENTED**
5. **Citation verification**: Validate LLM answers against sources
6. **Conversation memory**: Multi-turn Q&A with context (partially implemented in chats)
7. **Document summarization**: Auto-generate document summaries
8. **Named entity extraction**: Index by entities (people, places, etc.)
9. **Semantic caching**: Cache query embeddings and results
10. **Feedback loop**: Learn from user ratings to improve retrieval

---

## 🔗 Useful Links

- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard
- Gemini API Docs: https://ai.google.dev/gemini-api/docs
- Qdrant Docs: https://qdrant.tech/documentation/

---

## 📞 Session Handoff Notes

**For next session:**

1. **To continue development**: `docker-compose up -d` (backend auto-starts with Gemini embeddings)
2. **Recent context**:
   - Evaluation framework built and operational
   - Gemini embeddings (gemini-embedding-001) replacing sentence-transformers
   - Semantic similarity: 0.742 → 0.897 (+21% vs Claude.ai gold standard)
   - Next improvement: semantic chunking (Phase 3)
3. **Test Suite**: 136 tests all passing (eval scripts run separately)
4. **Current doc_id**: `4c12f53c-363c-4ddf-812f-b1806c919f01` (FX5U manual)
5. **Suggested next task**: Semantic chunking or query decomposition
6. **No blockers**: System stable

**Run evaluation:**

```bash
# Run benchmark eval
docker-compose run --rm \
  -e GEMINI_API_KEY=$GEMINI_API_KEY2 \
  -e QDRANT_HOST=qdrant -e QDRANT_PORT=6333 \
  -e EMBEDDING_MODEL=gemini-embedding-001 -e EMBEDDING_DIM=768 \
  -e GEMINI_MODEL=gemini-2.5-flash \
  -e USE_RERANKING=true -e USE_HYBRID_SEARCH=true \
  -e USE_QUERY_EXPANSION=true -e USE_RRF=true \
  test python evaluation/run_evaluation.py \
    --dataset evaluation/datasets/fx5u_qa_benchmark.json \
    --doc-ids 4c12f53c-363c-4ddf-812f-b1806c919f01 \
    --output evaluation/results/latest.json --no-judge

# Compare two runs
python evaluation/run_evaluation.py \
  --compare evaluation/results/baseline.json evaluation/results/latest.json \
  --output evaluation/results/comparison.html
```
