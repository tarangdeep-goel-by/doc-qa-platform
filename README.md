# Document Q&A Platform

A RAG (Retrieval Augmented Generation) platform for uploading large documents and answering questions using semantic search + LLM generation.

## Features

### Core Functionality
- **Document Upload**: Upload PDF documents with automatic processing and indexing
- **Smart Chunking**: Intelligent text chunking with overlap for better context
- **Multi-Chat System**: Create multiple chat sessions with different document sets
- **Chat Persistence**: All conversations saved with full message history

### Advanced Search
- **Hybrid Search**: Combines vector similarity (semantic) + BM25 (keyword) search
- **Reranking**: Cross-encoder reranking for improved result relevance
- **Document Filtering**: Search within specific documents or across all documents
- **Confidence Thresholds**: Configurable minimum score for answer quality

### AI & Citations
- **AI-Powered Q&A**: Answer questions using Google Gemini 2.5 Flash
- **Source Citations**: Every answer includes source documents with page numbers
- **Clickable PDF Links**: View exact source pages in browser
- **Context-Aware**: Maintains conversation history within each chat

### Robustness
- **Deleted Document Handling**: Graceful handling when documents are removed
- **Error Messaging**: Clear, actionable error messages for users
- **Comprehensive Testing**: 107 automated tests ensuring reliability

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript with Zustand state management
- **Vector DB**: Qdrant (self-hosted via Docker)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (384-dim, local)
- **LLM**: Google Gemini 2.5 Flash
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **Keyword Search**: BM25 (rank-bm25)
- **Document Processing**: PyPDF2
- **Testing**: Pytest (107 tests)

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Google Gemini API key

### Installation

1. **Clone and navigate to project**:
   ```bash
   cd doc-qa-platform
   ```

2. **Start Qdrant**:
   ```bash
   docker-compose up -d
   ```

3. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   Edit `backend/.env` and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

5. **Start the API**:
   ```bash
   python run_api.py
   ```

6. **Access the API**:
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health
   - Qdrant dashboard: http://localhost:6333/dashboard

## Usage

### Upload a Document

```bash
curl -X POST http://localhost:8000/api/admin/upload \
  -F "file=@your_document.pdf"
```

Response:
```json
{
  "doc_id": "abc-123-def",
  "title": "Your Document",
  "status": "success",
  "chunk_count": 342,
  "processing_time": 12.5
}
```

### Ask a Question

**Search all documents:**
```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic of chapter 3?",
    "top_k": 5
  }'
```

**Search specific documents:**
```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the FX5U models?",
    "top_k": 5,
    "doc_ids": ["de2c1151-6401-4659-b03b-1d9d1da9ef1c"]
  }'
```

**Search multiple documents:**
```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is habit stacking?",
    "doc_ids": ["doc-id-1", "doc-id-2"]
  }'
```

Response:
```json
{
  "question": "What is the main topic of chapter 3?",
  "answer": "Based on the document, chapter 3 focuses on...",
  "sources": [
    {
      "doc_id": "abc-123-def",
      "doc_title": "Your Document",
      "chunk_text": "Chapter 3 discusses...",
      "score": 0.95
    }
  ],
  "retrieved_count": 5
}
```

### List Documents

```bash
curl http://localhost:8000/api/admin/documents
```

### Delete a Document

```bash
curl -X DELETE http://localhost:8000/api/admin/documents/{doc_id}
```

## API Endpoints

### Chat Endpoints (`/api/chats`)

- `POST /api/chats` - Create new chat session
- `GET /api/chats` - List all chats
- `GET /api/chats/{chat_id}` - Get chat with messages
- `POST /api/chats/{chat_id}/ask` - Ask question in chat context
- `PUT /api/chats/{chat_id}/rename` - Rename chat
- `DELETE /api/chats/{chat_id}` - Delete chat

### Admin Endpoints (`/api/admin`)

- `POST /api/admin/upload` - Upload a document
- `GET /api/admin/documents` - List all documents
- `GET /api/admin/documents/{doc_id}` - Get document details
- `GET /api/admin/documents/{doc_id}/file` - Download/view PDF
- `DELETE /api/admin/documents/{doc_id}` - Delete a document

### Query Endpoints (`/api/query`)

- `POST /api/query/ask` - Ask a question (legacy, optional `doc_ids` filter)
- `GET /api/query/documents` - List available documents

### System Endpoints

- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## Project Structure

```
doc-qa-platform/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   ├── routers/
│   │   │   ├── admin.py         # Admin endpoints
│   │   │   └── query.py         # Query endpoints
│   │   └── schemas.py           # Pydantic models
│   ├── src/
│   │   ├── document_processor.py   # PDF extraction
│   │   ├── chunker.py              # Text chunking
│   │   ├── embedder.py             # Embeddings
│   │   ├── vector_store.py         # Qdrant wrapper
│   │   ├── qa_engine.py            # RAG pipeline
│   │   └── models.py               # Data models
│   ├── data/
│   │   ├── uploads/             # Uploaded files
│   │   └── documents.json       # Metadata
│   ├── requirements.txt
│   ├── run_api.py
│   └── .env
├── qdrant_storage/              # Qdrant data
├── docker-compose.yml
├── CLAUDE.md
└── README.md
```

## Configuration

Edit `backend/.env` to configure:

- `GEMINI_API_KEY` - Your Google Gemini API key
- `API_HOST` - API server host (default: 0.0.0.0)
- `API_PORT` - API server port (default: 8000)
- `QDRANT_HOST` - Qdrant host (default: localhost)
- `QDRANT_PORT` - Qdrant port (default: 6333)
- `CHUNK_SIZE` - Text chunk size (default: 1000)
- `CHUNK_OVERLAP` - Chunk overlap (default: 200)
- `TOP_K_RESULTS` - Default number of results (default: 5)

## How It Works

### Document Ingestion Pipeline

1. **Upload** → PDF file uploaded via API
2. **Extract** → Text extracted page-by-page
3. **Chunk** → Text split into 1000-char chunks with 200-char overlap
4. **Embed** → Each chunk converted to 384-dim vector
5. **Store** → Vectors + metadata stored in Qdrant

### Query Pipeline (RAG)

1. **Embed Query** → Question converted to 384-dim vector
2. **Hybrid Search** →
   - Vector search (semantic similarity)
   - BM25 search (keyword matching)
   - Fusion with weighted scoring (default: 50/50)
3. **Reranking** → Cross-encoder reranks results for relevance
4. **Quality Check** → Filter results below confidence threshold
5. **Retrieve** → Get chunk text + metadata + page numbers
6. **Generate** → Send context + question to Gemini with chat history
7. **Return** → Answer + source citations with page links

## Performance

- **Upload**: ~10-30s for typical book (200 pages)
- **Query**: ~2-3s for answer generation
- **Embedding**: ~50ms per chunk (CPU)
- **Search**: <100ms for 1M vectors

## Development

### Run in Development Mode

```bash
cd backend
python run_api.py
```

The API will auto-reload on code changes.

### Run Tests

**Run all 107 tests:**
```bash
docker-compose run --rm test
```

**Run specific test file:**
```bash
docker-compose run --rm test pytest tests/test_api.py -v
```

**Run with coverage:**
```bash
docker-compose run --rm test pytest --cov=src --cov-report=html
```

**Test categories:**
- API endpoints (19 tests)
- BM25 index (17 tests)
- Hybrid search (13 tests)
- QA guardrails (14 tests)
- RAG pipeline (16 tests)
- Reranker (14 tests)
- Deleted documents (14 tests)

### View Qdrant Dashboard

Access http://localhost:6333/dashboard to:
- View collections
- Inspect vectors
- Monitor performance

### Test with Sample Document

```bash
# Upload a test PDF
curl -X POST http://localhost:8000/api/admin/upload \
  -F "file=@sample.pdf"

# Ask a question
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

## Troubleshooting

### Qdrant Connection Failed

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Restart Qdrant
docker-compose restart qdrant
```

### Embedding Model Not Found

The first run will download the embedding model (~100MB). Ensure you have internet connection.

### Out of Memory

If processing very large documents, reduce `CHUNK_SIZE` in `.env`.

## Completed Features ✅

- ✅ Frontend UI (React + TypeScript)
- ✅ Multi-chat system with conversation history
- ✅ Hybrid search (vector + BM25)
- ✅ Reranking with cross-encoder
- ✅ Page number tracking and clickable citations
- ✅ Document filtering per chat
- ✅ Deleted document handling
- ✅ Comprehensive test suite (107 tests)

## Future Enhancements

- [ ] Support DOCX, HTML, TXT formats
- [ ] User authentication & authorization
- [ ] Document versioning
- [ ] Export Q&A sessions (PDF, Markdown)
- [ ] Document metadata filtering (date, type, tags)
- [ ] Advanced analytics and usage tracking
- [ ] Multi-language support
- [ ] Mobile-responsive UI improvements

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
