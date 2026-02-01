# Document Q&A Platform - Development Planner

**Last Updated**: 2026-02-01

---

## Backlog

### [FEATURE-007] Semantic Chunking
**Priority**: High
**Description**: Replace fixed-size chunking with semantic boundary detection (Max-Min algorithm). Keeps tables/lists intact instead of splitting mid-content.
**Expected Impact**: +10-15% answer quality
**Sub-Tickets**:
- [ ] [SUB-007-A] Implement sentence-level semantic similarity scoring
- [ ] [SUB-007-B] Max-Min breakpoint detection algorithm
- [ ] [SUB-007-C] Integration with document processor pipeline
- [ ] [SUB-007-D] Re-index documents with semantic chunks
- [ ] [SUB-007-E] Run eval and compare vs fixed-size chunking
- [ ] [SUB-007-F] Tests

### [FEATURE-008] Query Decomposition
**Priority**: Medium
**Description**: Break complex multi-faceted questions into sub-questions, answer each, synthesize. PruneRAG-inspired confidence-guided approach.
**Expected Impact**: +15-20% on complex questions
**Sub-Tickets**:
- [ ] [SUB-008-A] Question complexity classifier
- [ ] [SUB-008-B] LLM-based query decomposition
- [ ] [SUB-008-C] Parallel sub-question answering
- [ ] [SUB-008-D] Answer synthesis with confidence scoring
- [ ] [SUB-008-E] Run eval and compare
- [ ] [SUB-008-F] Tests

---

## In Progress

(Empty)

---

### Known Issues
None currently!


## Done

### [FEATURE-EVL] Evaluation Framework & RAG Quality Improvements ✅
**Priority**: High
**Description**: Automated eval framework measuring answer quality vs Claude.ai gold standard, plus systematic improvements (Gemini embeddings, enhanced BM25, chunk deduplication)
**Branch**: main
**Status**: Completed 2026-02-01
**Results**: Semantic similarity 0.742 → 0.897 (+21%)
**Sub-Tickets**:
- [x] [SUB-EVL-A] Evaluation framework (metrics, reporters, benchmark dataset)
- [x] [SUB-EVL-B] upload_and_eval.py one-command script
- [x] [SUB-EVL-C] Baseline evaluation run
- [x] [SUB-EVL-D] Enable reranking + fix confidence threshold bug (+5%)
- [x] [SUB-EVL-E] Switch to Gemini embeddings (gemini-embedding-001, 768-dim) (+15%)
- [x] [SUB-EVL-F] Enhanced BM25 tokenization (stop words, regex tokenizer)
- [x] [SUB-EVL-G] Chunk deduplication (Jaccard similarity)
- [x] [SUB-EVL-H] Update docker-compose and .env.example



### [FEATURE-000] Core RAG Platform - Full Stack MVP ✅
**Priority**: High
**Description**: Full-stack RAG platform with React frontend, FastAPI backend, Qdrant vector DB, Gemini LLM
**Branch**: main
**Status**: Completed 2026-01-31
**Sub-Tickets**:
- [x] [SUB-000-A] FastAPI backend structure
- [x] [SUB-000-B] Docker Compose setup (Qdrant)
- [x] [SUB-000-C] Document processing pipeline (PDF, chunking, embeddings)
- [x] [SUB-000-D] Vector storage (Qdrant)
- [x] [SUB-000-E] Basic RAG pipeline (semantic search + Gemini)
- [x] [SUB-000-F] Hybrid search (vector + BM25)
- [x] [SUB-000-G] Query expansion
- [x] [SUB-000-H] Reciprocal Rank Fusion (RRF)
- [x] [SUB-000-I] Cross-encoder reranking with position-aware blending
- [x] [SUB-000-J] Multi-chat system
- [x] [SUB-000-K] Deleted document handling
- [x] [SUB-000-L] Admin API endpoints
- [x] [SUB-000-M] Chat API endpoints
- [x] [SUB-000-N] Query API endpoints
- [x] [SUB-000-O] React frontend (TypeScript, Zustand, Tailwind, editorial design)
- [x] [SUB-000-P] Chat interface with multi-chat support
- [x] [SUB-000-Q] Document management UI
- [x] [SUB-000-R] Type-safe API client
- [x] [SUB-000-S] 136 comprehensive backend tests (all passing)
- [x] [SUB-000-T] Documentation (README, CLAUDE.md, PROJECT_STATUS)

**Completion Date**: 2026-01-31

---

## Implementation Notes

### Tech Stack (Current)
**Frontend**: React 18, TypeScript, Zustand, React Router, Tailwind CSS, Vite
**Backend**: FastAPI, Qdrant, Gemini embeddings (gemini-embedding-001), Google Gemini 2.5 Flash, BM25, cross-encoder
**Database**: Qdrant (vectors), JSON (metadata)
**Testing**: Pytest (136 backend tests)
**Infrastructure**: Docker Compose

### Architecture Decisions
1. **Qdrant over Pinecone** - Self-hosted, production-ready, no vendor lock-in
2. **Gemini 2.5 Flash** - Large context window (1M+ tokens), fast, cheap
3. **Hybrid search (vector + BM25)** - Better recall than pure semantic search
4. **RRF fusion** - More robust than weighted averaging
5. **Position-aware reranking** - Context-sensitive score blending
6. **Multi-chat system** - Organize conversations by topic/document
7. **Soft delete pattern** - Preserve chat history when documents deleted

### Current Status
- **Backend Tests**: 136/136 passing ✅
- **Frontend Tests**: Not yet implemented ⚠️
- **Docker**: All services running ✅
- **API**: Fully documented at /docs ✅
- **Backend Coverage**: >80% ✅

## Future Enhancements 

### [FEATURE-001] Additional Document Formats
**Priority**: High
**Description**: Support DOCX, HTML, TXT in addition to PDF
**Branch**: feature/001-document-formats
**Sub-Tickets**:
- [ ] [SUB-001-A] Add python-docx dependency
- [ ] [SUB-001-B] DOCX text extraction
- [ ] [SUB-001-C] HTML support (BeautifulSoup4)
- [ ] [SUB-001-D] Plain TXT support
- [ ] [SUB-001-E] Unified document processor interface
- [ ] [SUB-001-F] File type validation
- [ ] [SUB-001-G] Tests for each format
- [ ] [SUB-001-H] Update API docs

### [FEATURE-002] Frontend UX Improvements
**Priority**: Medium
**Description**: Keyboard shortcuts, markdown rendering, code highlighting, copy buttons
**Branch**: feature/002-frontend-ux
**Sub-Tickets**:
- [ ] [SUB-002-A] Keyboard shortcuts (Cmd+K for new chat, Escape to close modals)
- [ ] [SUB-002-B] Markdown rendering in assistant answers
- [ ] [SUB-002-C] Code syntax highlighting
- [ ] [SUB-002-D] Copy to clipboard buttons (code blocks, answers)
- [ ] [SUB-002-E] Loading skeletons for better perceived performance
- [ ] [SUB-002-F] Tests for new UI components

### [FEATURE-003] Frontend Testing
**Priority**: High
**Description**: Add comprehensive test coverage for React frontend
**Branch**: feature/003-frontend-testing
**Sub-Tickets**:
- [ ] [SUB-003-A] Vitest + React Testing Library setup
- [ ] [SUB-003-B] Component tests (chat, sidebar, modals)
- [ ] [SUB-003-C] Store tests (Zustand actions)
- [ ] [SUB-003-D] API client tests (mocked responses)
- [ ] [SUB-003-E] Integration tests (user flows)
- [ ] [SUB-003-F] E2E tests (Playwright) for critical paths
- [ ] [SUB-003-G] CI/CD pipeline integration

### [FEATURE-004] Search History & Export
**Priority**: Medium
**Description**: Track search history and export Q&A sessions
**Branch**: feature/004-search-history
**Sub-Tickets**:
- [ ] [SUB-004-A] Search history database schema
- [ ] [SUB-004-B] Track queries and results
- [ ] [SUB-004-C] History API endpoints
- [ ] [SUB-004-D] Export to markdown
- [ ] [SUB-004-E] Export to PDF
- [ ] [SUB-004-F] Frontend history view
- [ ] [SUB-004-G] Tests

### [FEATURE-005] Production Readiness
**Priority**: Medium
**Description**: Authentication, PostgreSQL, caching, logging for production
**Branch**: feature/005-production-ready
**Sub-Tickets**:
- [ ] [SUB-005-A] JWT authentication
- [ ] [SUB-005-B] PostgreSQL metadata store (replace JSON)
- [ ] [SUB-005-C] Redis caching for frequent queries
- [ ] [SUB-005-D] Async document processing with status polling
- [ ] [SUB-005-E] Rate limiting
- [ ] [SUB-005-F] Structured logging (JSON logs)
- [ ] [SUB-005-G] Health checks for all dependencies
- [ ] [SUB-005-H] Prometheus metrics
- [ ] [SUB-005-I] Tests for new features
- [ ] [SUB-005-J] Deployment guide

### [FEATURE-006] Advanced RAG Features
**Priority**: Low
**Description**: Multi-modal RAG, adaptive chunking, citation verification
**Branch**: feature/006-advanced-rag
**Sub-Tickets**:
- [ ] [SUB-006-A] Image/table extraction from PDFs
- [ ] [SUB-006-B] Adaptive chunking by document structure
- [ ] [SUB-006-C] Citation verification
- [ ] [SUB-006-D] Document summarization
- [ ] [SUB-006-E] Named entity extraction
- [ ] [SUB-006-F] Semantic caching
- [ ] [SUB-006-G] Tests

---

## Project Metadata

**Repository**: https://github.com/<your-username>/doc-qa-platform
**Owner**: tarangdeep-goel-by
**Started**: 2026-01-01 (estimated)
**MVP Completed**: 2026-01-31
**Status**: ✅ Full-stack production-ready MVP

---
**To resume:**
```bash
cd ./

# Start services
docker-compose up -d

# Terminal 1: Backend
cd backend && python run_api.py

# Terminal 2: Frontend
cd frontend && npm run dev

# Access: http://localhost:3000
```
