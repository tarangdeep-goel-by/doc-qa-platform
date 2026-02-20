"""FastAPI application for document Q&A platform.

Supports two modes:
- SaaS (JWT_SECRET set): Full JWT auth, multi-user, role-based access
- B2C  (JWT_SECRET empty): Open access, no login required
"""

import logging
import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from api.auth import AUTH_ENABLED
from api.schemas import HealthResponse
from src.embedder import Embedder
from src.vector_store import VectorStore
from src.qa_engine import QAEngine
from src.models import DocumentStore
from src.chat_manager import ChatManager
from src.rag_config import RAGConfig
from src.interaction_logger import InteractionLogger
from src.feedback_store import FeedbackStore

# Load environment variables
load_dotenv()

# Configure structured logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


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

    logger.info("Initializing application...")

    # Initialize user store (SaaS mode only)
    if AUTH_ENABLED:
        from src.user_store import UserStore
        logger.info("Initializing user store...")
        user_store = UserStore(db_path=os.path.join(data_dir, "users.db"))
        app.state.user_store = user_store
    else:
        app.state.user_store = None
        logger.info("Auth disabled — running in open/B2C mode")

    # Initialize components
    logger.info("Loading embedder...")
    embedder = Embedder(
        model_name=embedding_model,
        gemini_api_key=gemini_api_key,
        output_dimensionality=embedding_dim,
    )

    logger.info("Connecting to Qdrant...")
    vector_store = VectorStore(
        host=qdrant_host,
        port=qdrant_port,
        collection_name="documents",
        vector_size=embedding_dim,
        bm25_cache_dir=bm25_cache_dir
    )

    logger.info("Initializing document store...")
    document_store = DocumentStore(data_dir=data_dir)

    logger.info("Initializing chat manager...")
    chat_manager = ChatManager(base_dir=data_dir)

    fast_model = os.environ.get("GEMINI_FAST_MODEL", gemini_model)

    logger.info("Initializing QA engine...")
    qa_engine = QAEngine(
        embedder=embedder,
        vector_store=vector_store,
        gemini_api_key=gemini_api_key,
        model_name=gemini_model,
        use_reranker=use_reranking,
        reranker_model=reranker_model,
        fast_model_name=fast_model
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
    app.state.rag_config = RAGConfig.from_env()
    app.state.interaction_logger = InteractionLogger(data_dir=data_dir)
    app.state.feedback_store = FeedbackStore(data_dir=data_dir)

    logger.info("Application initialized successfully!")

    yield

    # Cleanup
    logger.info("Shutting down application...")
    try:
        vector_store.client.close()
        logger.info("Qdrant client closed")
    except Exception:
        logger.warning("Failed to close Qdrant client", exc_info=True)
    logging.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Document Q&A SaaS Platform",
    description="RAG-based SaaS platform for document Q&A with JWT auth",
    version="2.0.0",
    lifespan=lifespan
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler — never leak internals
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if os.environ.get("COOKIE_SECURE", "true").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers (imported here to avoid circular imports)
from .routers import admin, query, chats
if AUTH_ENABLED:
    from .routers import auth_router
    app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Document Q&A SaaS API",
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
        gemini_configured=gemini_configured,
        auth_required=AUTH_ENABLED,
    )
