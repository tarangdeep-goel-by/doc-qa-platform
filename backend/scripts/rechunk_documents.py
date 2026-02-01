#!/usr/bin/env python3
"""
Migration script to re-chunk existing documents with new chunk size parameters.

This script:
1. Loads all documents from the document store
2. Re-processes each document with new chunk size (2500 chars) and overlap (500 chars)
3. Regenerates embeddings for the new chunks
4. Replaces old chunks in Qdrant with new chunks
5. Updates document metadata with new chunk counts

Usage:
    python scripts/rechunk_documents.py

Prerequisites:
    - All services must be running (Qdrant, etc.)
    - GEMINI_API_KEY must be set in .env
    - Update CHUNK_SIZE and CHUNK_OVERLAP in .env before running
"""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from src.models import DocumentStore, DocumentChunk
from src.document_processor import DocumentProcessor
from src.chunker import TextChunker
from src.semantic_chunker import SemanticChunker
from src.embedder import Embedder
from src.vector_store import VectorStore

# Load environment variables
env_path = backend_dir / ".env"
load_dotenv(env_path)


def rechunk_document(
    doc_metadata,
    document_store: DocumentStore,
    chunker: TextChunker,
    embedder: Embedder,
    vector_store: VectorStore,
    processor: DocumentProcessor
):
    """
    Re-chunk a single document with new parameters.

    Args:
        doc_metadata: DocumentMetadata object
        document_store: DocumentStore instance
        chunker: TextChunker with new chunk size/overlap
        embedder: Embedder instance
        vector_store: VectorStore instance
        processor: DocumentProcessor instance
    """
    print(f"\n{'='*80}")
    print(f"Processing: {doc_metadata.filename}")
    print(f"Document ID: {doc_metadata.doc_id}")
    print(f"Current chunk count: {doc_metadata.chunk_count}")

    # Extract text from document
    try:
        page_data, metadata = processor.process_document(
            doc_metadata.file_path,
            doc_metadata.format
        )
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        return False

    # Chunk with new parameters
    chunk_data = chunker.chunk_with_page_tracking(page_data)
    new_chunk_count = len(chunk_data)
    print(f"New chunk count: {new_chunk_count} (was {doc_metadata.chunk_count})")

    if not chunk_data:
        print(f"❌ No chunks created for {doc_metadata.filename}")
        return False

    # Create document chunks
    doc_title = metadata.get('title') or doc_metadata.filename
    chunks = [
        DocumentChunk(
            text=chunk['text'],
            doc_id=doc_metadata.doc_id,
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

    # Delete old chunks from Qdrant
    print("Deleting old chunks from Qdrant...")
    try:
        vector_store.delete_document(doc_metadata.doc_id)
        print("✓ Old chunks deleted")
    except Exception as e:
        print(f"Warning: Error deleting old chunks: {e}")
        print("Continuing anyway...")

    # Store new chunks in Qdrant
    print("Storing new chunks in Qdrant...")
    chunk_payloads = [c.to_payload() for c in chunks]
    chunks_added = vector_store.add_document_chunks(chunk_payloads, embeddings)
    print(f"✓ Stored {chunks_added} chunks in Qdrant")

    # Update document metadata
    doc_metadata.chunk_count = new_chunk_count
    document_store.save_document(doc_metadata)
    print(f"✓ Updated document metadata")

    return True


def main():
    """Main migration function."""
    print("="*80)
    print("Document Re-chunking Migration Script")
    print("="*80)

    # Load configuration from .env
    data_dir = os.getenv("DATA_DIR", "data")
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    chunk_size = int(os.getenv("CHUNK_SIZE", "2500"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "500"))
    use_semantic = os.getenv("USE_SEMANTIC_CHUNKING", "false").lower() == "true"

    print(f"\nConfiguration:")
    print(f"  Data directory: {data_dir}")
    print(f"  Qdrant: {qdrant_host}:{qdrant_port}")
    print(f"  Embedding model: {embedding_model}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Chunk overlap: {chunk_overlap}")
    print(f"  Semantic chunking: {use_semantic}")

    # Initialize components
    print("\nInitializing components...")
    document_store = DocumentStore(data_dir=data_dir)
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    embedding_dim = int(os.getenv("EMBEDDING_DIM", "384"))
    embedder = Embedder(
        model_name=embedding_model,
        gemini_api_key=gemini_api_key,
        output_dimensionality=embedding_dim,
    )
    if use_semantic:
        chunker = SemanticChunker(embedder=embedder)
    else:
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    vector_store = VectorStore(
        host=qdrant_host, port=qdrant_port, vector_size=embedding_dim
    )
    processor = DocumentProcessor()
    print("✓ Components initialized")

    # Load all documents
    documents = document_store.list_documents()
    total_docs = len(documents)

    if total_docs == 0:
        print("\n⚠️  No documents found in the document store.")
        print("Nothing to migrate.")
        return

    print(f"\n📚 Found {total_docs} document(s) to re-chunk")

    # Ask for confirmation
    response = input("\nProceed with re-chunking? This will replace all existing chunks. (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Migration cancelled.")
        return

    # Process each document
    success_count = 0
    failed_count = 0

    for i, doc in enumerate(documents, 1):
        print(f"\n[{i}/{total_docs}]", end=" ")
        try:
            success = rechunk_document(
                doc,
                document_store,
                chunker,
                embedder,
                vector_store,
                processor
            )
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1

    # Summary
    print(f"\n{'='*80}")
    print("Migration Complete!")
    print(f"{'='*80}")
    print(f"✓ Successfully re-chunked: {success_count} document(s)")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} document(s)")
    print()


if __name__ == "__main__":
    main()
