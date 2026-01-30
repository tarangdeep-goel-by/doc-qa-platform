"""Chat session endpoints for multi-chat interface."""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Request

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
    SourceInfo
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


@router.post("/{chat_id}/ask", response_model=AskInChatResponse)
async def ask_in_chat(request: Request, chat_id: str, body: AskInChatRequest):
    """
    Ask a question in a chat context.

    Uses chat's associated documents and maintains conversation history.
    """
    chat_manager = request.app.state.chat_manager
    qa_engine = request.app.state.qa_engine
    document_store = request.app.state.document_store

    # Get chat
    chat, messages = chat_manager.get_chat(chat_id)

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        # Filter to only existing documents
        available_doc_ids = [
            doc_id for doc_id in chat.doc_ids
            if document_store.get_document(doc_id) is not None
        ] if chat.doc_ids else []

        # If no documents available, return early
        if not available_doc_ids:
            # Create user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role="user",
                content=body.question,
                timestamp=datetime.now().isoformat(),
                filtered_docs=[]
            )
            chat_manager.add_message(chat_id, user_message)

            # Create assistant message with helpful error
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role="assistant",
                content=(
                    "I cannot answer questions for this chat because all associated "
                    "documents have been deleted. Please add new documents to continue."
                ),
                timestamp=datetime.now().isoformat(),
                sources=[],
                filtered_docs=[]
            )
            chat_manager.add_message(chat_id, assistant_message)

            return AskInChatResponse(
                message=MessageResponse(
                    id=assistant_message.id,
                    chat_id=assistant_message.chat_id,
                    role=assistant_message.role,
                    content=assistant_message.content,
                    timestamp=assistant_message.timestamp,
                    sources=[],
                    filtered_docs=assistant_message.filtered_docs
                )
            )

        # Run RAG pipeline with available documents only
        result = qa_engine.answer_question(
            question=body.question,
            top_k=body.top_k,
            doc_ids=available_doc_ids,
            chat_history=chat.gemini_chat_history
        )

        # Create user message
        user_message = ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role="user",
            content=body.question,
            timestamp=datetime.now().isoformat(),
            filtered_docs=available_doc_ids
        )
        chat_manager.add_message(chat_id, user_message)

        # Convert sources to dicts
        sources_dicts = [
            {
                "doc_id": s["doc_id"],
                "doc_title": s["doc_title"],
                "chunk_text": s["chunk_text"],
                "score": s["score"],
                "page_num": s.get("page_num")
            }
            for s in result["sources"]
        ]

        # Create assistant message
        assistant_message = ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role="assistant",
            content=result["answer"],
            timestamp=datetime.now().isoformat(),
            sources=sources_dicts,
            filtered_docs=available_doc_ids
        )
        chat_manager.add_message(chat_id, assistant_message)

        # Update Gemini chat history (if provided by QA engine)
        if "gemini_history" in result:
            chat_manager.update_gemini_history(chat_id, result["gemini_history"])

        # Return assistant message
        return AskInChatResponse(
            message=MessageResponse(
                id=assistant_message.id,
                chat_id=assistant_message.chat_id,
                role=assistant_message.role,
                content=assistant_message.content,
                timestamp=assistant_message.timestamp,
                sources=[SourceInfo(**s) for s in sources_dicts],
                filtered_docs=assistant_message.filtered_docs
            )
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")
