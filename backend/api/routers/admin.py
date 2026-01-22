"""Admin endpoints for document management."""

import os
import time
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse

from api.schemas import (
    UploadResponse,
    DocumentListResponse,
    DocumentInfo,
    DocumentDetailResponse,
    DeleteResponse
)
from src.models import DocumentMetadata, DocumentChunk
from src.document_processor import DocumentProcessor
from src.chunker import TextChunker

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Upload and process a document.

    Accepts: PDF files
    Returns: Document ID and processing stats
    """
    start_time = time.time()

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Get app state
    embedder = request.app.state.embedder
    vector_store = request.app.state.vector_store
    document_store = request.app.state.document_store
    upload_dir = request.app.state.upload_dir

    # Check for duplicate by filename
    duplicate = document_store.find_by_filename(file.filename)

    if duplicate:
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": "duplicate_document",
                "message": f"Document '{file.filename}' already exists",
                "existing_doc_id": duplicate.doc_id,
                "existing_upload_date": duplicate.upload_date,
                "suggestion": "Use the existing document or rename your file"
            }
        )

    # Generate document ID
    doc_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1]
    saved_filename = f"{doc_id}.{file_extension}"
    file_path = os.path.join(upload_dir, saved_filename)

    try:
        # Save uploaded file
        print(f"Saving file: {file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process document
        print(f"Processing document: {file.filename}")
        processor = DocumentProcessor()
        page_data, metadata = processor.process_document(file_path, file_extension)

        # Get file size
        file_size_mb = processor.get_file_size_mb(file_path)

        # Chunk text with page tracking
        print("Chunking text...")
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
        chunk_data = chunker.chunk_with_page_tracking(page_data)
        print(f"Created {len(chunk_data)} chunks")

        if not chunk_data:
            raise ValueError("No text chunks created from document")

        # Create document chunks
        doc_title = metadata.get('title') or file.filename
        chunks = [
            DocumentChunk(
                text=chunk['text'],
                doc_id=doc_id,
                doc_title=doc_title,
                chunk_index=i,
                page_num=chunk['page_num'],
                metadata=metadata
            )
            for i, chunk in enumerate(chunk_data)
        ]

        # Generate embeddings
        print("Generating embeddings...")
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(chunk_texts)
        print(f"Generated {len(embeddings)} embeddings")

        # Store in Qdrant
        print("Storing in Qdrant...")
        chunk_payloads = [c.to_payload() for c in chunks]
        chunks_added = vector_store.add_document_chunks(chunk_payloads, embeddings)
        print(f"Stored {chunks_added} chunks in Qdrant")

        # Save document metadata
        doc_metadata = DocumentMetadata(
            doc_id=doc_id,
            title=doc_title,
            filename=file.filename,
            file_path=file_path,
            format=file_extension,
            upload_date=datetime.now().isoformat(),
            file_size_mb=file_size_mb,
            chunk_count=len(chunk_data),
            total_pages=metadata.get('total_pages'),
            metadata=metadata
        )
        document_store.save_document(doc_metadata)

        processing_time = time.time() - start_time
        print(f"Document processed successfully in {processing_time:.2f}s")

        return UploadResponse(
            doc_id=doc_id,
            title=doc_title,
            status="success",
            chunk_count=len(chunk_data),
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        # Cleanup on error
        if os.path.exists(file_path):
            os.remove(file_path)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(request: Request):
    """List all uploaded documents."""
    document_store = request.app.state.document_store

    docs = document_store.list_documents()

    document_infos = [
        DocumentInfo(
            doc_id=doc.doc_id,
            title=doc.title,
            upload_date=doc.upload_date,
            file_size_mb=doc.file_size_mb,
            chunk_count=doc.chunk_count,
            format=doc.format
        )
        for doc in docs
    ]

    return DocumentListResponse(documents=document_infos)


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(request: Request, doc_id: str):
    """Get detailed information about a document."""
    document_store = request.app.state.document_store

    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        doc_id=doc.doc_id,
        title=doc.title,
        filename=doc.filename,
        format=doc.format,
        upload_date=doc.upload_date,
        file_size_mb=doc.file_size_mb,
        chunk_count=doc.chunk_count,
        total_pages=doc.total_pages,
        metadata=doc.metadata
    )


@router.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(request: Request, doc_id: str):
    """Delete a document and its chunks from the system."""
    vector_store = request.app.state.vector_store
    document_store = request.app.state.document_store
    chat_manager = request.app.state.chat_manager

    # Get document metadata
    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete from Qdrant
        print(f"Deleting chunks from Qdrant for doc_id: {doc_id}")
        vector_store.delete_document(doc_id)

        # Delete file from disk
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            print(f"Deleted file: {doc.file_path}")

        # Delete metadata
        document_store.delete_document(doc_id)
        print(f"Deleted document metadata: {doc_id}")

        # Update all chats to remove this doc_id
        all_chats = chat_manager.list_chats()
        chats_updated = 0

        for chat in all_chats:
            if doc_id in chat.doc_ids:
                # Remove the doc_id from the chat
                chat.doc_ids = [id for id in chat.doc_ids if id != doc_id]
                # Save the updated chat
                chat_manager.save_chat(chat)
                chats_updated += 1

        message = f"Document '{doc.title}' deleted successfully"
        if chats_updated > 0:
            message += f". Updated {chats_updated} chat(s)"

        return DeleteResponse(
            success=True,
            message=message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/documents/{doc_id}/file")
async def download_document(request: Request, doc_id: str):
    """
    Serve the PDF file for a document.

    Can be opened in browser with #page=N anchor for specific pages.
    """
    document_store = request.app.state.document_store

    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    return FileResponse(
        doc.file_path,
        media_type='application/pdf',
        filename=doc.filename
    )
