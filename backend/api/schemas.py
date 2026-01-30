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
class ChatUsageInfo(BaseModel):
    """Information about a chat using a document."""
    id: str
    name: str


class DocumentInfo(BaseModel):
    """Document information for listing."""
    doc_id: str
    title: str
    upload_date: str
    file_size_mb: float
    chunk_count: int
    format: str
    chat_count: int = Field(default=0, description="Number of chats using this document")
    chats: List[ChatUsageInfo] = Field(default_factory=list, description="List of chats using this document")


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


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple documents."""
    doc_ids: List[str] = Field(..., min_length=1, description="List of document IDs to delete")


class DocumentDeleteResult(BaseModel):
    """Result of deleting a single document."""
    doc_id: str
    success: bool
    message: str


class BulkDeleteResponse(BaseModel):
    """Response after bulk deleting documents."""
    results: List[DocumentDeleteResult]
    total: int
    successful: int
    failed: int


# Query Request
class QueryRequest(BaseModel):
    """Request for asking a question."""
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    doc_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to filter search")

    # Advanced RAG options (optional - defaults from env if not provided)
    use_hybrid: Optional[bool] = Field(default=None, description="Use hybrid search (vector + BM25)")
    hybrid_alpha: Optional[float] = Field(default=None, ge=0, le=1, description="Hybrid weight (0=BM25, 1=vector)")
    use_reranking: Optional[bool] = Field(default=None, description="Use cross-encoder reranking")
    use_query_expansion: Optional[bool] = Field(default=None, description="Generate alternative query phrasings")
    use_rrf: Optional[bool] = Field(default=None, description="Use Reciprocal Rank Fusion")
    rerank_blending: Optional[str] = Field(default=None, description="Reranking blend strategy: 'position_aware' or 'replace'")


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


class BulkDeleteChatsRequest(BaseModel):
    """Request to delete multiple chats."""
    chat_ids: List[str] = Field(..., min_length=1, description="List of chat IDs to delete")


class ChatDeleteResult(BaseModel):
    """Result of deleting a single chat."""
    chat_id: str
    success: bool
    message: str


class BulkDeleteChatsResponse(BaseModel):
    """Response after bulk deleting chats."""
    results: List[ChatDeleteResult]
    total: int
    successful: int
    failed: int
