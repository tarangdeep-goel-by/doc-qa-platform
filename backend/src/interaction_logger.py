"""Append-only JSONL interaction logger for Q&A tracking."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class InteractionLogger:
    """Thread-safe append-only JSONL logger for Q&A interactions."""

    def __init__(self, data_dir: str = "data"):
        self.file_path = Path(data_dir) / "interactions.jsonl"
        self._lock = threading.Lock()

    def log_interaction(
        self,
        chat_id: str,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        latency_ms: int,
        doc_ids: List[str],
        config: Dict[str, Any],
        message_id: Optional[str] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chat_id": chat_id,
            "message_id": message_id,
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "doc_id": s.get("doc_id", ""),
                    "doc_title": s.get("doc_title", ""),
                    "score": s.get("score", 0),
                    "chunk_text": s.get("chunk_text", "")[:200],
                }
                for s in sources
            ],
            "latency_ms": latency_ms,
            "doc_ids": doc_ids,
            "config": config,
        }
        with self._lock:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def get_interactions(
        self, limit: int = 100, chat_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        entries = []
        with open(self.file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if chat_id and entry.get("chat_id") != chat_id:
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

        # Return most recent first
        return entries[-limit:][::-1]
