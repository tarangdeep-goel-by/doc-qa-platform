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
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim = int(os.getenv("EMBEDDING_DIM", "384"))
    data_dir = os.getenv("DATA_DIR", "data")
    upload_dir = os.getenv("UPLOAD_DIR", "data/uploads")
    use_reranking = os.getenv("USE_RERANKING", "true").lower() == "true"

    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    print("Initializing application...")

    # Initialize components
    print("Loading embedder...")
    embedder = Embedder(model_name=embedding_model)

    print("Connecting to Qdrant...")
    vector_store = VectorStore(
        host=qdrant_host,
        port=qdrant_port,
        collection_name="documents",
        vector_size=embedding_dim
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
        use_reranker=use_reranking
    )

    # Store in app state
    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.document_store = document_store
    app.state.chat_manager = chat_manager
    app.state.qa_engine = qa_engine
    app.state.upload_dir = upload_dir

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
