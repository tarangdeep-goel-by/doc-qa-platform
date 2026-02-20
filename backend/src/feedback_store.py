"""Append-only JSONL feedback store for thumbs up/down on answers."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeedbackStore:
    """Thread-safe append-only JSONL store for answer feedback."""

    def __init__(self, data_dir: str = "data"):
        self.file_path = Path(data_dir) / "feedback.jsonl"
        self._lock = threading.Lock()

    def add_feedback(
        self,
        message_id: str,
        chat_id: str,
        feedback: str,
        question: str,
        answer: str,
        doc_ids: List[str],
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": message_id,
            "chat_id": chat_id,
            "feedback": feedback,
            "question": question,
            "answer": answer,
            "doc_ids": doc_ids,
            "sources": sources or [],
        }
        with self._lock:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def get_feedback(
        self,
        limit: int = 100,
        chat_id: Optional[str] = None,
        feedback_filter: Optional[str] = None,
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
                    if feedback_filter and entry.get("feedback") != feedback_filter:
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

        # Return most recent first
        return entries[-limit:][::-1]
