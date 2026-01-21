# CLAUDE.md - Document Q&A Platform Development Guide

This file provides guidance to Claude Code when working on the Document Q&A Platform.

## Project Information

**GitHub Repository**: https://github.com/tarangdeep-goel-by/doc-qa-platform
**Owner**: tarangdeep-goel-by

## Project Overview

A RAG (Retrieval Augmented Generation) platform for uploading documents and answering questions using semantic search + LLM generation.

**Tech Stack:**
- Backend: FastAPI (Python)
- Vector DB: Qdrant (self-hosted, Docker)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (local, free, 384-dim)
- LLM: Google Gemini 2.0 Flash
- Document Processing: PyPDF2 (PDF only currently)

## Architecture

### Document Ingestion Pipeline

**Flow**: Upload → Extract → Chunk → Embed → Store

1. **DocumentProcessor** (`src/document_processor.py`)
   - Extracts text from PDF using PyPDF2
   - Captures metadata (pages, author, title)
   - Currently PDF-only; designed to add DOCX/HTML support later

2. **Chunker** (`src/chunker.py`)
   - Splits text into 1000-char chunks with 200-char overlap
   - Smart splitting: prefers paragraph/sentence boundaries
   - Maintains context across chunks

3. **Embedder** (`src/embedder.py`)
   - Uses `sentence-transformers/all-MiniLM-L6-v2`
   - Generates 384-dim vectors
   - Batches chunks for efficiency (batch_size=32)

4. **VectorStore** (`src/vector_store.py`)
   - Wraps Qdrant client
   - Collection: "documents" with cosine similarity
   - Payload schema: {text, doc_id, doc_title, chunk_index, metadata}

### Query Pipeline (RAG)

**Flow**: Question → Embed → Search → Retrieve → Generate

1. **QAEngine** (`src/qa_engine.py`)
   - Embeds question using same embedder
   - Searches Qdrant for top-k similar chunks (default k=5)
   - Builds context from retrieved chunks
   - Sends to Gemini with prompt template
   - Returns answer + source citations

### Data Models

**DocumentMetadata** (`src/models.py`):
- Stored in `data/documents.json`
- Fields: doc_id, title, filename, file_path, format, upload_date, file_size_mb, chunk_count, total_pages, metadata

**DocumentChunk** (`src/models.py`):
- Represents text chunk with metadata
- Fields: text, doc_id, doc_title, chunk_index, metadata

**DocumentStore** (`src/models.py`):
- Simple JSON-based store for document metadata
- Methods: save_document, get_document, delete_document, list_documents

## API Structure

### FastAPI App (`api/main.py`)

- Uses lifespan events for initialization
- Creates shared state: embedder, vector_store, document_store, qa_engine
- Includes CORS middleware
- Routes: admin (upload/manage), query (Q&A)

### Admin Router (`api/routers/admin.py`)

- `POST /api/admin/upload`: Upload & process document (synchronous)
- `GET /api/admin/documents`: List all documents
- `GET /api/admin/documents/{doc_id}`: Get document details
- `DELETE /api/admin/documents/{doc_id}`: Delete document + chunks

### Query Router (`api/routers/query.py`)

- `POST /api/query/ask`: Ask question (runs RAG pipeline)
- `GET /api/query/documents`: List available documents

### Schemas (`api/schemas.py`)

Pydantic models for request/response validation:
- UploadResponse, DocumentInfo, DocumentListResponse
- DocumentDetailResponse, DeleteResponse
- QueryRequest, QueryResponse, SourceInfo
- HealthResponse

## Key Design Decisions

### Why These Technologies?

**Qdrant**: Free, self-hosted, production-ready, handles millions of vectors

**sentence-transformers/all-MiniLM-L6-v2**: Free, local, fast (~50ms/chunk), good quality

**Gemini 2.0 Flash**: Large context (1M+ tokens), fast, cheap, strong instruction following

**1000-char chunks + 200-char overlap**: Balances semantic coherence with LLM context limits

### File Storage

- Original files: `data/uploads/{doc_id}.{ext}`
- Metadata: `data/documents.json`
- Vectors: Qdrant storage (Docker volume)

### Processing Strategy

- **Synchronous upload**: Blocks until complete (~10-30s typical)
- Future: Could add async processing with status polling
- Logs progress to console for debugging

## Development Patterns

### Adding New Document Formats

1. Add processor to `DocumentProcessor.process_document()`
2. Extract text + metadata consistently
3. Update requirements.txt with new libraries
4. Update upload validation in admin router
5. Test end-to-end

Example skeleton:
```python
def extract_text_from_docx(file_path: str) -> Tuple[str, Dict]:
    # Use python-docx
    # Extract paragraphs
    # Build metadata
    return full_text, metadata
```

### Modifying Chunk Size/Overlap

Update `.env`:
```env
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
```

Then initialize chunker:
```python
chunker = TextChunker(
    chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
    chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200))
)
```

### Changing Embedding Model

1. Update `.env`:
   ```env
   EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
   EMBEDDING_DIM=768
   ```

2. Recreate Qdrant collection (dimension must match)

3. Re-upload all documents

### Customizing Gemini Prompt

Edit `QAEngine._build_prompt()` in `src/qa_engine.py`:
```python
def _build_prompt(self, question: str, context: str) -> str:
    # Modify prompt template
    # Add constraints, examples, etc.
    return prompt
```

## Common Tasks

### Testing Document Upload

```bash
# Start Qdrant
docker-compose up -d

# Start API
cd backend && python run_api.py

# Upload test PDF
curl -X POST http://localhost:8000/api/admin/upload \
  -F "file=@test.pdf"

# Check Qdrant dashboard
open http://localhost:6333/dashboard
```

### Debugging Query Results

1. Check retrieved chunks:
   - Inspect `sources` in response
   - Verify relevance scores (>0.7 is good)

2. Test search directly:
   ```python
   from src.embedder import Embedder
   from src.vector_store import VectorStore

   embedder = Embedder()
   vector_store = VectorStore()

   query_vec = embedder.embed_text("test question")
   results = vector_store.search(query_vec, top_k=5)
   ```

3. Inspect Gemini input:
   - Add logging to `QAEngine._generate_answer()`
   - Print full prompt before generation

### Adding New Endpoints

1. Create schema in `api/schemas.py`
2. Add endpoint to appropriate router
3. Use `get_app_state()` to access components
4. Handle errors with HTTPException
5. Test with curl or in `/docs`

### Database Migrations

Currently uses simple JSON store. To migrate to PostgreSQL:

1. Add SQLAlchemy to requirements
2. Create `src/database.py` with models
3. Replace `DocumentStore` with DB queries
4. Update routers to use new store
5. Keep Qdrant for vectors (no change)

## Environment Variables

**Required:**
- `GEMINI_API_KEY` - Must be set

**Optional (with defaults):**
- `API_HOST=0.0.0.0`
- `API_PORT=8000`
- `QDRANT_HOST=localhost`
- `QDRANT_PORT=6333`
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `EMBEDDING_DIM=384`
- `CHUNK_SIZE=1000`
- `CHUNK_OVERLAP=200`
- `TOP_K_RESULTS=5`

## Testing Strategy

### Manual Testing Workflow

1. Upload document
2. Verify chunks created (check response)
3. Ask specific question about content
4. Check sources match expected sections
5. Try edge cases:
   - Very short question
   - Question about missing topic
   - Multiple documents

### Unit Testing (Future)

```bash
# Add to requirements.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Create tests/
# - test_chunker.py
# - test_embedder.py
# - test_vector_store.py
# - test_qa_engine.py

# Run
pytest tests/
```

## Performance Optimization

### Current Performance

- Upload: ~10-30s for 200-page book
- Query: ~2-3s total
  - Embedding: ~50ms
  - Search: ~50ms
  - Generation: 1-2s

### Optimization Opportunities

1. **Faster embeddings**: Use GPU if available
   ```python
   embedder = Embedder()
   if torch.cuda.is_available():
       embedder.model = embedder.model.to('cuda')
   ```

2. **Batch processing**: Upload multiple docs in parallel

3. **Caching**: Cache frequent queries
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def cached_embed(text: str):
       return embedder.embed_text(text)
   ```

4. **Async processing**: Make upload async with status endpoint

## Troubleshooting

### "No text could be extracted from PDF"

- PDF might be image-based (scanned)
- Add OCR support with pytesseract
- Or try different PDF library (pdfplumber, PyMuPDF)

### "Qdrant connection failed"

```bash
# Check Qdrant status
docker ps | grep qdrant

# View logs
docker logs doc-qa-qdrant

# Restart
docker-compose restart qdrant
```

### "Out of memory during embedding"

- Reduce batch_size in `Embedder.embed_texts()`
- Process documents in smaller chunks
- Or add more RAM / use swap

### Low relevance scores (<0.5)

- Question may be too vague
- Document may not contain info
- Try rephrasing question
- Check if chunks are too small/large

## Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions focused (single responsibility)
- Prefer explicit over implicit
- Handle errors gracefully (try/except with clear messages)

## Git Workflow

```bash
# Feature branch
git checkout -b feature/add-docx-support

# Make changes
# Test locally
# Commit
git commit -m "Add DOCX support to DocumentProcessor"

# Push
git push origin feature/add-docx-support

# Create PR
```

## Next Steps / Roadmap

**Phase 1: Additional Formats**
- Add DOCX support (python-docx)
- Add HTML support (BeautifulSoup4)
- Add TXT support (simple read)

**Phase 2: Frontend**
- Build React + TypeScript admin UI
- Build user Q&A chat interface
- Document upload with drag-drop

**Phase 3: Advanced Features**
- User authentication (JWT)
- Document versioning
- Question history
- Export Q&A sessions
- Filter by document in queries

**Phase 4: Production**
- Add PostgreSQL for metadata
- Add Redis for caching
- Add async processing
- Add monitoring (Prometheus)
- Add logging (structured JSON)
- Add tests (pytest)
- Add CI/CD (GitHub Actions)

## Contact

For issues or questions, refer to the main project documentation or create an issue.
