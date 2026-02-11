"""Chat session endpoints for multi-chat interface."""

import json
import logging
import time
import uuid

logger = logging.getLogger(__name__)
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.schemas import (
    CreateChatRequest,
    ChatResponse,
    ChatListResponse,
    ChatDetailResponse,
    MessageResponse,
    AskInChatRequest,
    AskInChatResponse,
    RenameChatRequest,
    DeleteChatResponse,
    BulkDeleteChatsRequest,
    BulkDeleteChatsResponse,
    ChatDeleteResult,
    SourceInfo,
    FeedbackRequest,
    FeedbackResponse,
)
from src.models import ChatMessage

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def create_chat(request: Request, body: CreateChatRequest):
    """
    Create a new chat session.

    Associates specific documents with this chat.
    """
    chat_manager = request.app.state.chat_manager

    # Create chat
    chat = chat_manager.create_chat(
        name=body.name,
        doc_ids=body.doc_ids
    )

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(request: Request):
    """List all chat sessions sorted by updated_at (newest first)."""
    chat_manager = request.app.state.chat_manager

    chats = chat_manager.list_chats()

    chat_responses = [
        ChatResponse(
            id=chat.id,
            name=chat.name,
            doc_ids=chat.doc_ids,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            message_count=chat.message_count
        )
        for chat in chats
    ]

    return ChatListResponse(chats=chat_responses)


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(request: Request, chat_id: str):
    """Get chat details with all messages."""
    chat_manager = request.app.state.chat_manager
    document_store = request.app.state.document_store

    chat, messages = chat_manager.get_chat(chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Validate documents still exist
    missing_docs = []
    available_docs = []

    for doc_id in chat.doc_ids:
        doc = document_store.get_document(doc_id)
        if doc:
            available_docs.append({
                "doc_id": doc.doc_id,
                "title": doc.title
            })
        else:
            missing_docs.append(doc_id)

    chat_response = ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count
    )

    message_responses = [
        MessageResponse(
            id=msg.id,
            chat_id=msg.chat_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            sources=[SourceInfo(**s) for s in msg.sources] if msg.sources else None,
            filtered_docs=msg.filtered_docs
        )
        for msg in messages
    ]

    return ChatDetailResponse(
        chat=chat_response,
        messages=message_responses,
        missing_documents=missing_docs,
        available_documents=available_docs
    )


@router.patch("/{chat_id}", response_model=ChatResponse)
async def rename_chat(request: Request, chat_id: str, body: RenameChatRequest):
    """Rename a chat."""
    chat_manager = request.app.state.chat_manager

    success = chat_manager.rename_chat(chat_id, body.name)

    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Get updated chat
    chat, _ = chat_manager.get_chat(chat_id)

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count
    )


@router.delete("/{chat_id}", response_model=DeleteChatResponse)
async def delete_chat(request: Request, chat_id: str):
    """Delete a chat and all its messages."""
    chat_manager = request.app.state.chat_manager

    success = chat_manager.delete_chat(chat_id)

    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")

    return DeleteChatResponse(
        success=True,
        message=f"Chat deleted successfully"
    )


@router.post("/bulk-delete", response_model=BulkDeleteChatsResponse)
async def bulk_delete_chats(request: Request, bulk_request: BulkDeleteChatsRequest):
    """
    Delete multiple chats at once.

    Returns status for each chat deletion attempt.
    """
    chat_manager = request.app.state.chat_manager

    results = []
    successful = 0
    failed = 0

    for chat_id in bulk_request.chat_ids:
        try:
            # Get chat info for better error message
            chat, _ = chat_manager.get_chat(chat_id)

            if not chat:
                results.append(ChatDeleteResult(
                    chat_id=chat_id,
                    success=False,
                    message="Chat not found"
                ))
                failed += 1
                continue

            # Delete chat
            success = chat_manager.delete_chat(chat_id)

            if success:
                results.append(ChatDeleteResult(
                    chat_id=chat_id,
                    success=True,
                    message=f"'{chat.name}' deleted"
                ))
                successful += 1
            else:
                results.append(ChatDeleteResult(
                    chat_id=chat_id,
                    success=False,
                    message="Delete failed"
                ))
                failed += 1

        except Exception as e:
            results.append(ChatDeleteResult(
                chat_id=chat_id,
                success=False,
                message=f"Failed: {str(e)}"
            ))
            failed += 1

    return BulkDeleteChatsResponse(
        results=results,
        total=len(bulk_request.chat_ids),
        successful=successful,
        failed=failed
    )


@router.post("/{chat_id}/ask")
async def ask_in_chat(request: Request, chat_id: str, body: AskInChatRequest):
    """
    Ask a question in a chat context. Returns SSE stream.

    Event format:
        data: {"type": "retrieval_done", "sources": [...]}\n\n
        data: {"type": "chunk", "content": "partial text..."}\n\n
        data: {"type": "done", "message_id": "uuid"}\n\n
        data: {"type": "error", "detail": "..."}\n\n
    """
    chat_manager = request.app.state.chat_manager
    qa_engine = request.app.state.qa_engine
    document_store = request.app.state.document_store

    # Validate chat exists (raise before streaming starts)
    chat, messages = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Filter to only existing documents; empty doc_ids means "search all"
    if chat.doc_ids:
        available_doc_ids = [
            doc_id for doc_id in chat.doc_ids
            if document_store.get_document(doc_id) is not None
        ]
    else:
        available_doc_ids = [doc.doc_id for doc in document_store.list_documents()]

    def _sse_event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    interaction_logger = request.app.state.interaction_logger
    rag_config = request.app.state.rag_config

    def event_generator():
        start_time = time.time()
        try:
            # Save user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role="user",
                content=body.question,
                timestamp=datetime.now().isoformat(),
                filtered_docs=available_doc_ids
            )
            chat_manager.add_message(chat_id, user_message)

            # Handle no documents case
            if not available_doc_ids:
                no_docs_content = (
                    "I cannot answer questions for this chat because all associated "
                    "documents have been deleted. Please add new documents to continue."
                )
                yield _sse_event({"type": "retrieval_done", "sources": []})
                yield _sse_event({"type": "chunk", "content": no_docs_content})

                assistant_message = ChatMessage(
                    id=str(uuid.uuid4()),
                    chat_id=chat_id,
                    role="assistant",
                    content=no_docs_content,
                    timestamp=datetime.now().isoformat(),
                    sources=[],
                    filtered_docs=[]
                )
                chat_manager.add_message(chat_id, assistant_message)
                yield _sse_event({"type": "done", "message_id": assistant_message.id})
                return

            # Stream RAG pipeline
            sources_dicts = []
            full_content = []

            for event in qa_engine.answer_question_stream(
                question=body.question,
                **rag_config.to_answer_kwargs(
                    doc_ids=available_doc_ids,
                    chat_history=chat.gemini_chat_history
                )
            ):
                if event["type"] == "retrieval_done":
                    sources_dicts = event["sources"]
                    yield _sse_event({"type": "retrieval_done", "sources": sources_dicts})

                elif event["type"] == "chunk":
                    full_content.append(event["content"])
                    yield _sse_event({"type": "chunk", "content": event["content"]})

                elif event["type"] == "done":
                    latency_ms = int((time.time() - start_time) * 1000)

                    # Save assistant message to disk
                    assistant_message = ChatMessage(
                        id=str(uuid.uuid4()),
                        chat_id=chat_id,
                        role="assistant",
                        content=event["full_content"],
                        timestamp=datetime.now().isoformat(),
                        sources=sources_dicts,
                        filtered_docs=available_doc_ids
                    )
                    chat_manager.add_message(chat_id, assistant_message)
                    yield _sse_event({"type": "done", "message_id": assistant_message.id})

                    # Log interaction
                    try:
                        interaction_logger.log_interaction(
                            chat_id=chat_id,
                            question=body.question,
                            answer=event["full_content"],
                            sources=sources_dicts,
                            latency_ms=latency_ms,
                            doc_ids=available_doc_ids,
                            config=rag_config.to_dict(),
                            message_id=assistant_message.id,
                        )
                    except Exception:
                        logger.exception("Failed to log interaction")

                elif event["type"] == "error":
                    yield _sse_event({"type": "error", "detail": event["detail"]})

        except Exception as e:
            logger.exception("Failed to stream answer in chat")
            yield _sse_event({"type": "error", "detail": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{chat_id}/messages/{message_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: Request, chat_id: str, message_id: str, body: FeedbackRequest
):
    """Submit thumbs up/down feedback on an assistant message."""
    chat_manager = request.app.state.chat_manager
    feedback_store = request.app.state.feedback_store

    chat, messages = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Find the assistant message
    target_msg = None
    question_text = ""
    for i, msg in enumerate(messages):
        if msg.id == message_id:
            if msg.role != "assistant":
                raise HTTPException(status_code=400, detail="Can only give feedback on assistant messages")
            target_msg = msg
            # Look back for the preceding user message
            if i > 0 and messages[i - 1].role == "user":
                question_text = messages[i - 1].content
            break

    if not target_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback_store.add_feedback(
        message_id=message_id,
        chat_id=chat_id,
        feedback=body.feedback,
        question=question_text,
        answer=target_msg.content,
        doc_ids=chat.doc_ids,
    )

    return FeedbackResponse(success=True)
