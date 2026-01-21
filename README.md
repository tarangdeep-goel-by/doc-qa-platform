# Document Q&A Platform

A RAG (Retrieval Augmented Generation) platform for uploading large documents and answering questions using semantic search + LLM generation.

## Features

- **Document Upload**: Upload PDF documents (support for DOCX, HTML, TXT coming soon)
- **Smart Chunking**: Intelligent text chunking with overlap for better context
- **Semantic Search**: Fast vector search using Qdrant
- **Document Filtering**: Search within specific documents or across all documents
- **AI-Powered Q&A**: Answer questions using Google Gemini 2.0 Flash
- **Source Citations**: Every answer includes source documents and relevance scores

## Tech Stack

- **Backend**: FastAPI (Python)
- **Vector DB**: Qdrant (self-hosted via Docker)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, free)
- **LLM**: Google Gemini 2.0 Flash
- **Document Processing**: PyPDF2

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

### Admin Endpoints (`/api/admin`)

- `POST /api/admin/upload` - Upload a document
- `GET /api/admin/documents` - List all documents
- `GET /api/admin/documents/{doc_id}` - Get document details
- `DELETE /api/admin/documents/{doc_id}` - Delete a document

### Query Endpoints (`/api/query`)

- `POST /api/query/ask` - Ask a question (optional `doc_ids` filter)
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

1. **Embed Query** → Question converted to vector
2. **Search** → Find top-5 most similar chunks in Qdrant
3. **Retrieve** → Get chunk text + metadata
4. **Generate** → Send context + question to Gemini
5. **Return** → Answer + source citations

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

## Future Enhancements

- [ ] Support DOCX, HTML, TXT formats
- [ ] User authentication
- [ ] Document versioning
- [ ] Question history
- [ ] Export Q&A sessions
- [ ] Frontend UI (React + TypeScript)
- [ ] Multi-document search with advanced filters
- [ ] Document metadata filtering (date, type, tags)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
