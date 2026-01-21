"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Upload Response
class UploadResponse(BaseModel):
    """Response after uploading a document."""
    doc_id: str
    title: str
    status: str
    chunk_count: int
    processing_time: float


# Document List Response
class DocumentInfo(BaseModel):
    """Document information for listing."""
    doc_id: str
    title: str
    upload_date: str
    file_size_mb: float
    chunk_count: int
    format: str


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: List[DocumentInfo]


# Document Detail Response
class DocumentDetailResponse(BaseModel):
    """Detailed document information."""
    doc_id: str
    title: str
    filename: str
    format: str
    upload_date: str
    file_size_mb: float
    chunk_count: int
    total_pages: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Delete Response
class DeleteResponse(BaseModel):
    """Response after deleting a document."""
    success: bool
    message: str


# Query Request
class QueryRequest(BaseModel):
    """Request for asking a question."""
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    doc_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to filter search")


# Source Information
class SourceInfo(BaseModel):
    """Information about a source chunk."""
    doc_id: str
    doc_title: str
    chunk_text: str
    score: float


# Query Response
class QueryResponse(BaseModel):
    """Response for a question."""
    question: str
    answer: str
    sources: List[SourceInfo]
    retrieved_count: int


# Health Check
class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    qdrant_connected: bool
    gemini_configured: bool
