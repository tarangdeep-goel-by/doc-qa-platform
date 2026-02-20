"""Chat session endpoints for multi-chat interface."""

import json
import logging
import time
import uuid

logger = logging.getLogger(__name__)
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

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
from api.auth import get_current_user
from src.models import ChatMessage
from src.user_store import User
from src.doc_router import route_query

router = APIRouter()


def _verify_chat_owner(chat, user: User):
    """Return 404 if chat doesn't belong to user."""
    if chat.user_id and chat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.post("", response_model=ChatResponse)
async def create_chat(request: Request, body: CreateChatRequest, user: User = Depends(get_current_user)):
    """Create a new chat session."""
    chat_manager = request.app.state.chat_manager

    chat = chat_manager.create_chat(
        name=body.name,
        doc_ids=body.doc_ids,
        auto_route=body.auto_route,
        user_id=user.id,
    )

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count,
        auto_route=chat.auto_route
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(request: Request, user: User = Depends(get_current_user)):
    """List user's chat sessions sorted by updated_at (newest first)."""
    chat_manager = request.app.state.chat_manager

    all_chats = chat_manager.list_chats()
    # Filter to user's chats only
    user_chats = [c for c in all_chats if c.user_id == user.id]

    chat_responses = [
        ChatResponse(
            id=chat.id,
            name=chat.name,
            doc_ids=chat.doc_ids,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            message_count=chat.message_count,
            auto_route=chat.auto_route
        )
        for chat in user_chats
    ]

    return ChatListResponse(chats=chat_responses)


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(request: Request, chat_id: str, user: User = Depends(get_current_user)):
    """Get chat details with all messages."""
    chat_manager = request.app.state.chat_manager
    document_store = request.app.state.document_store

    chat, messages = chat_manager.get_chat(chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    _verify_chat_owner(chat, user)

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
        message_count=chat.message_count,
        auto_route=chat.auto_route
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
async def rename_chat(request: Request, chat_id: str, body: RenameChatRequest, user: User = Depends(get_current_user)):
    """Rename a chat."""
    chat_manager = request.app.state.chat_manager

    chat, _ = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    _verify_chat_owner(chat, user)

    chat_manager.rename_chat(chat_id, body.name)
    chat, _ = chat_manager.get_chat(chat_id)

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count,
        auto_route=chat.auto_route
    )


@router.delete("/{chat_id}", response_model=DeleteChatResponse)
async def delete_chat(request: Request, chat_id: str, user: User = Depends(get_current_user)):
    """Delete a chat and all its messages."""
    chat_manager = request.app.state.chat_manager

    chat, _ = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    _verify_chat_owner(chat, user)

    chat_manager.delete_chat(chat_id)

    return DeleteChatResponse(
        success=True,
        message="Chat deleted successfully"
    )


@router.post("/bulk-delete", response_model=BulkDeleteChatsResponse)
async def bulk_delete_chats(request: Request, bulk_request: BulkDeleteChatsRequest, user: User = Depends(get_current_user)):
    """Delete multiple chats at once."""
    chat_manager = request.app.state.chat_manager

    results = []
    successful = 0
    failed = 0

    for chat_id in bulk_request.chat_ids:
        try:
            chat, _ = chat_manager.get_chat(chat_id)

            if not chat or (chat.user_id and chat.user_id != user.id):
                results.append(ChatDeleteResult(
                    chat_id=chat_id,
                    success=False,
                    message="Chat not found"
                ))
                failed += 1
                continue

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

        except Exception:
            logger.exception("Failed to delete chat %s in bulk", chat_id)
            results.append(ChatDeleteResult(
                chat_id=chat_id,
                success=False,
                message="Delete failed"
            ))
            failed += 1

    return BulkDeleteChatsResponse(
        results=results,
        total=len(bulk_request.chat_ids),
        successful=successful,
        failed=failed
    )


@router.delete("/{chat_id}/documents/{doc_id}", response_model=ChatResponse)
async def remove_chat_document(request: Request, chat_id: str, doc_id: str, user: User = Depends(get_current_user)):
    """Remove a document from a chat's doc_ids."""
    chat_manager = request.app.state.chat_manager

    chat, _ = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    _verify_chat_owner(chat, user)

    if doc_id not in chat.doc_ids:
        raise HTTPException(status_code=404, detail="Document not in this chat")

    chat.doc_ids = [d for d in chat.doc_ids if d != doc_id]
    chat_manager.save_chat(chat)

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        doc_ids=chat.doc_ids,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat.message_count,
        auto_route=chat.auto_route
    )


@router.post("/{chat_id}/ask")
@limiter.limit("30/minute")
async def ask_in_chat(request: Request, chat_id: str, body: AskInChatRequest, user: User = Depends(get_current_user)):
    """Ask a question in a chat context. Returns SSE stream."""
    chat_manager = request.app.state.chat_manager
    qa_engine = request.app.state.qa_engine
    document_store = request.app.state.document_store

    chat, messages = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    _verify_chat_owner(chat, user)

    # Auto-route: on first question, detect relevant docs via BM25
    routed_doc_ids = None
    if chat.auto_route and not chat.doc_ids and not messages:
        vector_store = request.app.state.vector_store
        routed_doc_ids = route_query(body.question, vector_store.bm25_index)
        if routed_doc_ids:
            chat.doc_ids = routed_doc_ids
        chat.auto_route = False
        chat_manager.save_chat(chat)

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

    STREAM_TIMEOUT = 300  # 5 minutes

    def event_generator():
        start_time = time.time()
        try:
            # Emit docs_routed event if auto-routing happened
            if routed_doc_ids is not None:
                doc_names = []
                for did in (routed_doc_ids or []):
                    doc = document_store.get_document(did)
                    doc_names.append(doc.title if doc else did)
                yield _sse_event({
                    "type": "docs_routed",
                    "doc_ids": routed_doc_ids or [],
                    "doc_names": doc_names,
                })

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
                if time.time() - start_time > STREAM_TIMEOUT:
                    yield _sse_event({"type": "error", "detail": "Stream timeout"})
                    return

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

                    # Update chat history for follow-ups (truncate answer to 300 chars)
                    try:
                        answer_summary = event["full_content"][:300]
                        history = list(chat.gemini_chat_history or [])
                        history.append({"question": body.question, "answer": answer_summary})
                        # Keep last 5 turns
                        chat_manager.update_gemini_history(chat_id, history[-5:])
                    except Exception:
                        logger.exception("Failed to update chat history")

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

        except Exception:
            logger.exception("Failed to stream answer in chat")
            yield _sse_event({"type": "error", "detail": "An error occurred while generating the answer"})

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
    request: Request, chat_id: str, message_id: str, body: FeedbackRequest,
    user: User = Depends(get_current_user),
):
    """Submit thumbs up/down feedback on an assistant message."""
    chat_manager = request.app.state.chat_manager
    feedback_store = request.app.state.feedback_store

    chat, messages = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    _verify_chat_owner(chat, user)

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
