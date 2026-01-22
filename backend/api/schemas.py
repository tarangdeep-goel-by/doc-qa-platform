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
    page_num: Optional[int] = None


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


# Chat Schemas
class CreateChatRequest(BaseModel):
    """Request to create a new chat."""
    name: str = Field(..., min_length=1, max_length=200)
    doc_ids: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Chat session response."""
    id: str
    name: str
    doc_ids: List[str]
    created_at: str
    updated_at: str
    message_count: int


class ChatListResponse(BaseModel):
    """List of chats."""
    chats: List[ChatResponse]


class MessageResponse(BaseModel):
    """Chat message response."""
    id: str
    chat_id: str
    role: str
    content: str
    timestamp: str
    sources: Optional[List[SourceInfo]] = None
    filtered_docs: Optional[List[str]] = None


class ChatDetailResponse(BaseModel):
    """Detailed chat with messages."""
    chat: ChatResponse
    messages: List[MessageResponse]
    missing_documents: List[str] = Field(default_factory=list, description="Document IDs that no longer exist")
    available_documents: List[Dict[str, str]] = Field(default_factory=list, description="Documents that are still available")


class AskInChatRequest(BaseModel):
    """Request to ask a question in a chat."""
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=20)


class AskInChatResponse(BaseModel):
    """Response to question in chat."""
    message: MessageResponse


class RenameChatRequest(BaseModel):
    """Request to rename a chat."""
    name: str = Field(..., min_length=1, max_length=200)


class DeleteChatResponse(BaseModel):
    """Response after deleting a chat."""
    success: bool
    message: str
