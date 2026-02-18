"""FastAPI application for document Q&A platform."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.schemas import HealthResponse
from src.embedder import Embedder
from src.vector_store import VectorStore
from src.qa_engine import QAEngine
from src.models import DocumentStore
from src.chat_manager import ChatManager

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    # Load configuration
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    gemini_model = os.environ["GEMINI_MODEL"]
    qdrant_host = os.environ["QDRANT_HOST"]
    qdrant_port = int(os.environ["QDRANT_PORT"])
    embedding_model = os.environ["EMBEDDING_MODEL"]
    embedding_dim = int(os.environ["EMBEDDING_DIM"])
    data_dir = os.environ["DATA_DIR"]
    upload_dir = os.environ["UPLOAD_DIR"]
    use_reranking = os.environ["USE_RERANKING"].lower() == "true"
    chunk_size = int(os.environ["CHUNK_SIZE"])
    chunk_overlap = int(os.environ["CHUNK_OVERLAP"])
    bm25_cache_dir = os.environ["BM25_CACHE_DIR"]
    reranker_model = os.environ["RERANKER_MODEL"]

    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    print("Initializing application...")

    # Initialize components
    print("Loading embedder...")
    embedder = Embedder(
        model_name=embedding_model,
        gemini_api_key=gemini_api_key,
        output_dimensionality=embedding_dim,
    )

    print("Connecting to Qdrant...")
    vector_store = VectorStore(
        host=qdrant_host,
        port=qdrant_port,
        collection_name="documents",
        vector_size=embedding_dim,
        bm25_cache_dir=bm25_cache_dir
    )

    print("Initializing document store...")
    document_store = DocumentStore(data_dir=data_dir)

    print("Initializing chat manager...")
    chat_manager = ChatManager(base_dir=data_dir)

    print("Initializing QA engine...")
    qa_engine = QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        model_name=gemini_model,
        use_reranker=use_reranking,
        reranker_model=reranker_model,
        fast_model_name=os.environ.get("GEMINI_FAST_MODEL"),
    )

    # Store in app state
    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.document_store = document_store
    app.state.chat_manager = chat_manager
    app.state.qa_engine = qa_engine
    app.state.upload_dir = upload_dir
    app.state.chunk_size = chunk_size
    app.state.chunk_overlap = chunk_overlap
    app.state.use_semantic_chunking = os.environ["USE_SEMANTIC_CHUNKING"].lower() == "true"

    print("Application initialized successfully!")

    yield

    # Cleanup
    print("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="Document Q&A Platform",
    description="RAG-based platform for uploading documents and asking questions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (imported here to avoid circular imports)
from .routers import admin, query, chats
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Document Q&A Platform API",
        "docs": "/docs",
        "health": "/health"
    }


# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    vector_store = getattr(app.state, "vector_store", None)

    qdrant_connected = vector_store.check_connection() if vector_store else False
    gemini_configured = os.getenv("GEMINI_API_KEY") is not None

    return HealthResponse(
        status="healthy" if qdrant_connected and gemini_configured else "unhealthy",
        qdrant_connected=qdrant_connected,
        gemini_configured=gemini_configured
    )
