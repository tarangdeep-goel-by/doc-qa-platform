# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information

**GitHub Repository**: https://github.com/tarangdeep-goel-by/doc-qa-platform
**Owner**: tarangdeep-goel-by

## Project Overview

A production-ready RAG (Retrieval Augmented Generation) platform for uploading documents and answering questions using advanced semantic search + LLM generation. Full-stack application with React frontend and FastAPI backend.

**Tech Stack:**

**Backend:**
- Framework: FastAPI (Python 3.11+)
- Vector DB: Qdrant (self-hosted, Docker)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (384-dim, local)
- LLM: Google Gemini 2.5 Flash
- Keyword Search: BM25 (rank-bm25)
- Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2
- Document Processing: PyPDF2
- Testing: Pytest (136 tests)

**Frontend:**
- Framework: React 18 + TypeScript + Vite
- State: Zustand (centralized store)
- Routing: React Router v7
- Styling: Tailwind CSS (editorial design system)
- UI: Lucide React icons
- Notifications: react-hot-toast

## Essential Commands

### Full Stack Development

```bash
# Start all services (Qdrant + backend)
docker-compose up -d

# Terminal 1: Backend
cd backend && python run_api.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Backend Only

```bash
# Start Qdrant + backend in Docker
docker-compose up -d

# View logs
docker-compose logs -f backend

# Rebuild after code changes
docker-compose build backend
docker-compose restart backend
```

### Frontend Only

```bash
# Install dependencies
cd frontend && npm install

# Development server (http://localhost:3000)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Testing

```bash
# Backend: Run all 136 tests (Docker - recommended)
docker-compose run --rm test

# Backend: Run specific test file
docker-compose run --rm test pytest tests/test_api.py -v

# Backend: Run specific test class
docker-compose run --rm test pytest tests/test_api.py::TestQueryDocuments -v

# Backend: With coverage report
docker-compose run --rm test pytest tests/ --cov=src --cov-report=html

# Backend: Quick integration tests (bash script)
cd backend && ./test_api.sh tests/fixtures/test.pdf

# Frontend: No test suite yet (future)
```

### Access Points

- **Frontend UI**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
- **Qdrant dashboard**: http://localhost:6333/dashboard

## High-Level Architecture

### Full Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 3000)                │
│  • Zustand state management (documents, chats, messages)    │
│  • React Router (/, /chat/:id, /documents)                  │
│  • Tailwind CSS (editorial design system)                   │
│  • API client (typed fetch wrapper)                         │
└─────────────────────────────────────────────────────────────┘
                             ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (Port 8000)                  │
│  • Three router groups: /api/admin, /api/chats, /api/query │
│  • Shared app state (lifespan events)                       │
│  • Pydantic schemas for validation                          │
└─────────────────────────────────────────────────────────────┘
         ↓                                    ↓
    ┌─────────┐                          ┌─────────┐
    │ Qdrant  │                          │ Gemini  │
    │ Vectors │                          │   API   │
    │  +BM25  │                          │(Gen+QE) │
    └─────────┘                          └─────────┘
```

### Three-Layer RAG Pipeline (Backend)

```
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                           │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. INGESTION: PDF → Extract → Chunk → Embed → Store         │
│     • PyPDF2 extracts text page-by-page                       │
│     • TextChunker: 1000-char chunks, 200-char overlap         │
│     • Embedder: all-MiniLM-L6-v2 (384-dim vectors)           │
│     • VectorStore: Qdrant + BM25 index                       │
│                                                                │
│  2. RETRIEVAL: Question → Multi-Strategy Search → Rerank     │
│     • Query Expansion: LLM generates variants (optional)     │
│     • Hybrid Search: Vector (semantic) + BM25 (keyword)      │
│     • RRF Fusion: Reciprocal Rank Fusion for score merging  │
│     • Reranking: Cross-encoder with position-aware blending  │
│                                                                │
│  3. GENERATION: Context + History → LLM → Answer + Sources  │
│     • Gemini 2.5 Flash with conversation history             │
│     • Source citations with page numbers                      │
│     • PDF links for exact source viewing                      │
│                                                                │
└──────────────────────────────────────────────────────────────┘
         ↓                                    ↓
    ┌─────────┐                          ┌─────────┐
    │ Qdrant  │                          │ Gemini  │
    │ Vectors │                          │   API   │
    │  +BM25  │                          │(Gen+QE) │
    └─────────┘                          └─────────┘
```

### Frontend Architecture

**State Management** (src/store/appStore.ts):
- Centralized Zustand store for all application state
- No local component state for server data
- Optimistic updates for messages (instant UI feedback)
- Auto-reload on mutations (upload/delete triggers refresh)

**Store structure:**
```typescript
{
  chats: Chat[]              // All user chats
  activeChat: Chat | null    // Currently open chat
  documents: Document[]      // All uploaded documents
  messages: ChatMessage[]    // Messages for activeChat only
  loading: boolean           // Global loading state
  error: string | null       // Global error state
}
```

**Key actions:**
- `loadChats()` - Fetch all chats from API
- `loadDocuments()` - Fetch all documents from API
- `setActiveChat(chatId)` - Load chat + messages
- `createChat(name, docIds)` - Create chat with document filter
- `sendMessage(question)` - Send message (optimistic update)
- `uploadDocument(file)` - Upload PDF with duplicate detection
- `deleteDocument(docId)` - Delete doc + update affected chats

**Routing** (React Router v7):
```
/ (AppLayout)
├── / (WelcomeScreen) - Chat list + new chat button
├── /chat/:chatId (ChatInterface) - Chat conversation
└── /documents (DocumentsPage) - Document management
```

**Design System** (Tailwind):
- Editorial aesthetic: magazine-style typography, serif fonts
- Color palette: cream (#faf9f7), ink (#1a1a2e), burgundy (#8b4049)
- Fluid typography: `text-fluid-{xs|sm|base|lg|xl|2xl|3xl}` (responsive without breakpoints)
- Typography: Fraunces (serif), Literata (body), Inter Variable (sans)

**API Client** (src/api/client.ts):
- Type-safe fetch wrapper (no direct fetch in components)
- All endpoints return typed responses
- Error handling with human-readable messages

### Backend Architecture

**Application State** (api/main.py):
- FastAPI lifespan events initialize shared components once at startup
- Components stored in `app.state`: embedder, vector_store, document_store, chat_manager, qa_engine
- Access via `get_app_state(request)` in routers

**Document Processing** (src/):
- `document_processor.py` - PDF text extraction with PyPDF2
- `chunker.py` - Smart text chunking (sentence-boundary aware)
- `embedder.py` - Embedding generation (batched for efficiency)
- `vector_store.py` - Qdrant wrapper + BM25 integration
- `bm25_index.py` - Persistent keyword search index

**Query Engine** (src/qa_engine.py):
- Orchestrates the full RAG pipeline
- Optional query expansion (LLM-generated variants)
- Calls VectorStore for hybrid search
- Applies reranking with position-aware blending
- Generates answer with Gemini using conversation history

**Chat System** (src/chat_manager.py):
- Multi-chat sessions with document associations
- Message persistence to `data/chats/{chat_id}.json`
- Automatic title generation from first question
- Soft delete pattern: maintains doc_id references after deletion

**Data Persistence**:
- Documents: `data/documents.json` (metadata), `data/uploads/` (PDFs)
- Chats: `data/chats/{chat_id}.json` (messages + metadata)
- Vectors: Qdrant Docker volume
- BM25 Index: `data/bm25/` (pickled corpus)

### API Structure

**Three router groups:**

1. **Admin** (`/api/admin/*`) - Document management
   - Upload, list, get details, delete documents
   - Serves PDF files for viewing

2. **Chats** (`/api/chats/*`) - Conversation management
   - Create, list, get, rename, delete chats
   - Ask questions in chat context (preserves history)

3. **Query** (`/api/query/*`) - Legacy Q&A endpoints
   - Stateless question answering
   - Document filtering support

### Advanced RAG Features

**Configurable via `.env`:**

```bash
# Query Expansion (adds 1-2s latency, +15-25% recall)
USE_QUERY_EXPANSION=false
QUERY_EXPANSION_VARIANTS=2

# Hybrid Search (vector + keyword)
USE_HYBRID_SEARCH=true
HYBRID_ALPHA=0.5  # 0=keyword only, 1=semantic only

# Reciprocal Rank Fusion (better than weighted averaging)
USE_RRF=true
RRF_K_PARAMETER=60

# Cross-encoder Reranking
USE_RERANKING=true
RERANKER_BLENDING=position_aware  # or "replace"
```

**Position-Aware Reranking** (src/reranker.py):
- Top 3 results: 75% retrieval weight, 25% reranker
- Ranks 4-10: 50/50 blend
- Ranks 11+: 25% retrieval, 75% reranker
- Preserves good initial rankings while improving lower ranks

### Deleted Document Handling

**Soft delete pattern:**
- Chats maintain `doc_ids` array even after document deletion
- RAG pipeline filters out deleted documents automatically
- Clear error messages when all chat documents are deleted
- Preserves chat history for audit trail

## Key Design Patterns

### Shared Application State

Components are initialized once at startup via FastAPI lifespan events and stored in `app.state`. Access in routers:

```python
def get_app_state(request: Request):
    return request.app.state

@router.post("/endpoint")
async def handler(request: Request):
    state = get_app_state(request)
    result = state.qa_engine.answer_question(...)
```

### Qdrant Payload Structure

Every chunk stored in Qdrant includes:

```python
{
    "text": "chunk content...",
    "doc_id": "uuid",
    "doc_title": "document.pdf",
    "chunk_index": 0,
    "page_number": 5,        # From PyPDF2
    "metadata": {...}        # PDF metadata
}
```

### Document Filtering

Use `MatchAny` filter in Qdrant to search specific documents:

```python
# In vector_store.py
if doc_ids:
    must_conditions.append(
        FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))
    )
```

## Key Design Patterns

### Frontend Patterns

**1. Optimistic Message Updates:**
When sending a message:
1. Immediately add user message to UI (`temp-${Date.now()}` ID)
2. Call API
3. Add assistant response when received
4. No loading spinner for user message (instant feedback)

**2. Document Filtering in Chats:**
Each chat has a fixed `doc_ids` array set at creation. Questions in that chat only search those documents.

Flow:
1. User clicks "New Chat"
2. Modal shows document selector (multi-select)
3. User selects documents + names chat
4. `createChat(name, docIds)` creates chat with filter
5. All questions in that chat use those doc_ids

**3. Error Handling:**
Pattern: Try/catch → Set error in store → Toast notification

```typescript
try {
  await api.uploadDocument(file)
  toast.success('Document uploaded successfully')
} catch (error) {
  const message = error instanceof Error ? error.message : 'Generic error'
  toast.error(message)
  throw error
}
```

**4. Modal Pattern:**
Controlled visibility via parent state

```typescript
const [isOpen, setIsOpen] = useState(false)

<NewChatModal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  onSuccess={(chat) => {
    navigate(`/chat/${chat.id}`)
    setIsOpen(false)
  }}
/>
```

### Backend Patterns

## Common Development Tasks

### Frontend Tasks

**Adding a New Page:**
1. Create component in `frontend/src/pages/`
2. Add route to `frontend/src/App.tsx`
3. Add navigation link to sidebar/header
4. Use `useAppStore()` to access state

**Adding a New API Endpoint (Frontend):**
1. Add types to `frontend/src/types/index.ts`
2. Add function to `frontend/src/api/client.ts`
3. Add action to `frontend/src/store/appStore.ts` (if needed)
4. Use in component via `useAppStore()`

**Modifying Design System:**
- Colors: Edit `frontend/tailwind.config.js` → `theme.extend.colors`
- Typography: Edit `frontend/tailwind.config.js` → `theme.extend.fontFamily`
- Fluid sizes: Edit `frontend/tailwind.config.js` → `theme.extend.fontSize`

### Backend Tasks

**Adding a New Document Format:**

1. Add extraction logic to `src/document_processor.py`
2. Update `requirements.txt` with new library
3. Update MIME type validation in `api/routers/admin.py`
4. Add tests to `tests/test_api.py`

### Modifying RAG Pipeline

1. Update logic in `src/qa_engine.py` or `src/vector_store.py`
2. Add configuration to `.env.example`
3. Add unit tests
4. Add integration test to `tests/test_rag_pipeline_integration.py`

**Adding a New API Endpoint (Backend):**
1. Define Pydantic schemas in `backend/api/schemas.py`
2. Add endpoint to appropriate router
3. Access components via `get_app_state(request)`
4. Add test to `backend/tests/test_api.py`
5. Update frontend API client (`frontend/src/api/client.ts`)
6. Add types to `frontend/src/types/index.ts`

### Debugging RAG Results

```python
# Add logging to qa_engine.py
import logging
logger = logging.getLogger(__name__)

# Log retrieved chunks
for result in results:
    logger.info(f"Score: {result.score}, Text: {result.payload['text'][:100]}")

# View logs
docker-compose logs backend | grep "Score:"
```

## Environment Configuration

**Required:**
- `GEMINI_API_KEY` - Must be set

**RAG Optimization Toggles:**
- `USE_HYBRID_SEARCH=true` - Enable BM25 + vector fusion
- `USE_RERANKING=true` - Enable cross-encoder reranking
- `USE_QUERY_EXPANSION=false` - Generate query variants (adds latency)
- `USE_RRF=true` - Use Reciprocal Rank Fusion
- `RERANKER_BLENDING=position_aware` - Context-aware score blending

**Performance:**
- `CHUNK_SIZE=1000` - Text chunk size
- `CHUNK_OVERLAP=200` - Chunk overlap
- `TOP_K_RESULTS=5` - Default retrieval count

See `.env.example` for full list.

## Testing Architecture

**136 tests across 8 test files:**

- `test_api.py` (24 tests) - API integration tests
- `test_bm25_index.py` (17 tests) - BM25 keyword search
- `test_hybrid_search.py` (18 tests) - Hybrid search + RRF
- `test_query_expansion.py` (10 tests) - Query expansion
- `test_reranker.py` (23 tests) - Reranker + position-aware blending
- `test_rag_pipeline_integration.py` (16 tests) - End-to-end RAG
- `test_qa_guardrails.py` (14 tests) - LLM guardrails
- `test_deleted_documents.py` (14 tests) - Deletion handling

**Test patterns:**
- Fixtures in `conftest.py` for shared setup
- Docker-based test runner for consistency
- Automatic cleanup after each test
- Integration tests use real services (Qdrant, Gemini)

## Project Structure

```
doc-qa-platform/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/               # ChatInterface, ChatMessageItem
│   │   │   ├── sidebar/            # Sidebar, ChatListItem
│   │   │   ├── modals/             # NewChatModal, UploadModal
│   │   │   └── welcome/            # WelcomeScreen
│   │   ├── layouts/
│   │   │   └── AppLayout.tsx       # Sidebar + content wrapper
│   │   ├── pages/
│   │   │   └── DocumentsPage.tsx   # Document management
│   │   ├── store/
│   │   │   └── appStore.ts         # Zustand store (single source of truth)
│   │   ├── api/
│   │   │   └── client.ts           # Type-safe API client
│   │   ├── types/
│   │   │   └── index.ts            # TypeScript type definitions
│   │   ├── App.tsx                 # Router setup
│   │   └── main.tsx                # React entry point
│   ├── tailwind.config.js          # Design system config
│   ├── vite.config.ts              # Vite + proxy config
│   ├── package.json
│   └── CLAUDE.md                   # Frontend-specific guidance
│
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI app, lifespan events
│   │   ├── routers/
│   │   │   ├── admin.py            # Document management
│   │   │   ├── chats.py            # Chat sessions
│   │   │   └── query.py            # Legacy Q&A
│   │   └── schemas.py              # Pydantic models
│   ├── src/
│   │   ├── document_processor.py   # PDF extraction
│   │   ├── chunker.py              # Text chunking
│   │   ├── embedder.py             # Embedding generation
│   │   ├── vector_store.py         # Qdrant + BM25
│   │   ├── bm25_index.py           # Keyword search index
│   │   ├── reranker.py             # Cross-encoder reranking
│   │   ├── qa_engine.py            # RAG orchestration
│   │   ├── chat_manager.py         # Chat persistence
│   │   └── models.py               # Data models
│   ├── tests/                      # 136 automated tests
│   ├── data/
│   │   ├── uploads/                # PDF files
│   │   ├── documents.json          # Document metadata
│   │   ├── chats/                  # Chat sessions
│   │   └── bm25/                   # BM25 index cache
│   ├── .env.example
│   ├── requirements.txt
│   └── CLAUDE.md                   # Backend-specific guidance
│
├── qdrant_storage/                 # Qdrant Docker volume
├── docker-compose.yml
├── PROJECT_STATUS.md               # Implementation tracker
└── README.md                       # User-facing docs
```

## Performance Metrics

**Expected performance:**
- Upload: ~10-30s for 200-page book
- Query (standard): ~2-3s (50ms embed + 100ms search + 1-2s LLM)
- Query (with expansion): ~3-5s (+1-2s for variant generation)
- Hybrid search: ~150ms (vector + BM25 + fusion)
- Reranking: ~200ms for 10 candidates

**Quality improvements (with all features enabled):**
- Recall: +15-25% (query expansion)
- Ranking quality: +5-10% (RRF)
- Top-k precision: +3-5% (position-aware reranking)
- **Overall: ~20-30% better answer quality**

## Troubleshooting

### Frontend Issues

**"API request failed":**
1. Check backend is running: `http://localhost:8000/docs`
2. Check proxy config in `frontend/vite.config.ts`
3. Inspect network tab for actual error

**"Document upload fails silently":**
1. Check file size (backend may have limits)
2. Check file format (PDF only currently)
3. Check backend logs for processing errors

**"Chat not loading messages":**
1. Check `activeChat` in store (may be null)
2. Verify `setActiveChat(chatId)` was called
3. Check network tab for `/api/chats/:id` response

**"Styles not updating":**
1. Restart dev server (Tailwind purge cache issue)
2. Check class name is in `content` paths (tailwind.config.js)
3. Verify class exists in Tailwind (check docs)

### Backend Issues

**Qdrant connection failed:**
```bash
docker ps | grep qdrant
docker logs doc-qa-qdrant
docker-compose restart qdrant
```

**Tests failing:**
```bash
docker-compose ps                      # Check all services running
docker-compose logs backend            # Check backend logs
docker-compose down && docker-compose up -d  # Full restart
```

**Low relevance scores:**
- Enable query expansion: `USE_QUERY_EXPANSION=true`
- Check chunk size (may be too large/small)
- Inspect retrieved chunks in response `sources`

## Important Notes

**For detailed frontend guidance**, see `frontend/CLAUDE.md` which includes:
- Component architecture and organization
- TypeScript patterns and type safety
- Styling conventions (Tailwind class order)
- Modal patterns and toast notifications
- Performance considerations (bundle size, API optimization)

**For detailed backend guidance**, see `backend/CLAUDE.md` which includes:
- Detailed RAG pipeline architecture
- Authentication & authorization (JWT)
- BM25 keyword search implementation
- Document processing pipeline details
- Chat management system
- Migration strategies
- Comprehensive troubleshooting

**For project status and recent changes**, see `PROJECT_STATUS.md`

**For user-facing documentation**, see `README.md`
