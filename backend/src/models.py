"""Data models for document storage and metadata."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional
import json
import os


@dataclass
class DocumentMetadata:
    """Metadata for uploaded documents."""
    doc_id: str
    title: str
    filename: str
    file_path: str
    format: str
    upload_date: str
    file_size_mb: float
    chunk_count: int = 0
    total_pages: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMetadata":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document."""
    text: str
    doc_id: str
    doc_title: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata
        }


class DocumentStore:
    """Simple JSON-based document metadata store."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.metadata_file = os.path.join(data_dir, "documents.json")
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w') as f:
                json.dump({}, f)

    def save_document(self, doc: DocumentMetadata):
        """Save document metadata."""
        docs = self.load_all()
        docs[doc.doc_id] = doc.to_dict()
        with open(self.metadata_file, 'w') as f:
            json.dump(docs, f, indent=2)

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Get document by ID."""
        docs = self.load_all()
        doc_data = docs.get(doc_id)
        return DocumentMetadata.from_dict(doc_data) if doc_data else None

    def delete_document(self, doc_id: str) -> bool:
        """Delete document metadata."""
        docs = self.load_all()
        if doc_id in docs:
            del docs[doc_id]
            with open(self.metadata_file, 'w') as f:
                json.dump(docs, f, indent=2)
            return True
        return False

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Load all documents."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def list_documents(self) -> list[DocumentMetadata]:
        """List all documents."""
        docs = self.load_all()
        return [DocumentMetadata.from_dict(d) for d in docs.values()]
