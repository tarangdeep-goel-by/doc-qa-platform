"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


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
    question: str = Field(..., min_length=1, max_length=5000)
    doc_ids: Optional[List[str]] = Field(default=None, max_length=50, description="Optional list of document IDs to filter search")


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
    auth_required: bool = True


# Chat Schemas
class CreateChatRequest(BaseModel):
    """Request to create a new chat."""
    name: str = Field(..., min_length=1, max_length=200)
    doc_ids: List[str] = Field(default_factory=list)
    auto_route: bool = Field(default=False, description="Auto-detect relevant documents from first question")


class ChatResponse(BaseModel):
    """Chat session response."""
    id: str
    name: str
    doc_ids: List[str]
    created_at: str
    updated_at: str
    message_count: int
    auto_route: bool = False


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
    question: str = Field(..., min_length=1, max_length=5000)


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


# Feedback Schemas
class FeedbackRequest(BaseModel):
    """Request to submit feedback on an answer."""
    feedback: Literal["up", "down"]


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool


# Auth Schemas
class LoginRequest(BaseModel):
    """Login request."""
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserInfo(BaseModel):
    """Public user info."""
    id: str
    email: str
    role: str
    features: Dict[str, bool] = Field(default_factory=dict)


class LoginResponse(BaseModel):
    """Login response with access token."""
    access_token: str
    user: UserInfo
