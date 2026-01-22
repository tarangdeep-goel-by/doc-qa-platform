"""Chat session manager for handling multi-chat conversations."""

from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import json
import uuid
from datetime import datetime

from .models import Chat, ChatMessage


class ChatManager:
    """Manages chat sessions and messages with JSON-based persistence."""

    def __init__(self, base_dir: str = "data"):
        """
        Initialize ChatManager.

        Args:
            base_dir: Base directory for data storage
        """
        self.base_dir = Path(base_dir)
        self.chats_dir = self.base_dir / "chats"
        self.chats_dir.mkdir(parents=True, exist_ok=True)

    def create_chat(self, name: str, doc_ids: List[str]) -> Chat:
        """
        Create a new chat session.

        Args:
            name: Chat name (or preview from first question)
            doc_ids: Document IDs associated with this chat

        Returns:
            Created Chat object
        """
        chat_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        chat = Chat(
            id=chat_id,
            name=name,
            doc_ids=doc_ids,
            created_at=now,
            updated_at=now,
            message_count=0,
            gemini_chat_history=[]
        )

        # Create chat directory
        chat_dir = self.chats_dir / chat_id
        chat_dir.mkdir(exist_ok=True)

        # Save metadata
        self._save_chat_metadata(chat)

        # Initialize empty messages file
        messages_file = chat_dir / "messages.json"
        with open(messages_file, 'w') as f:
            json.dump([], f)

        return chat

    def get_chat(self, chat_id: str) -> Tuple[Optional[Chat], List[ChatMessage]]:
        """
        Get chat and its messages.

        Args:
            chat_id: Chat ID

        Returns:
            Tuple of (Chat, List of ChatMessages) or (None, []) if not found
        """
        chat_dir = self.chats_dir / chat_id
        if not chat_dir.exists():
            return None, []

        # Load metadata
        metadata_file = chat_dir / "metadata.json"
        try:
            with open(metadata_file, 'r') as f:
                chat_data = json.load(f)
            chat = Chat.from_dict(chat_data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None, []

        # Load messages
        messages_file = chat_dir / "messages.json"
        try:
            with open(messages_file, 'r') as f:
                messages_data = json.load(f)
            messages = [ChatMessage.from_dict(m) for m in messages_data]
        except (FileNotFoundError, json.JSONDecodeError):
            messages = []

        return chat, messages

    def list_chats(self) -> List[Chat]:
        """
        List all chat sessions.

        Returns:
            List of Chat objects sorted by updated_at (newest first)
        """
        chats = []

        for chat_dir in self.chats_dir.iterdir():
            if not chat_dir.is_dir():
                continue

            metadata_file = chat_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, 'r') as f:
                    chat_data = json.load(f)
                chats.append(Chat.from_dict(chat_data))
            except (json.JSONDecodeError, TypeError):
                continue

        # Sort by updated_at (newest first)
        chats.sort(key=lambda c: c.updated_at, reverse=True)
        return chats

    def add_message(self, chat_id: str, message: ChatMessage) -> bool:
        """
        Add a message to a chat.

        Args:
            chat_id: Chat ID
            message: ChatMessage to add

        Returns:
            True if successful, False if chat not found
        """
        chat_dir = self.chats_dir / chat_id
        if not chat_dir.exists():
            return False

        # Load existing messages
        messages_file = chat_dir / "messages.json"
        try:
            with open(messages_file, 'r') as f:
                messages_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messages_data = []

        # Add new message
        messages_data.append(message.to_dict())

        # Save messages
        with open(messages_file, 'w') as f:
            json.dump(messages_data, f, indent=2)

        # Update chat metadata (updated_at and message_count)
        chat, _ = self.get_chat(chat_id)
        if chat:
            chat.updated_at = datetime.now().isoformat()
            chat.message_count = len(messages_data)
            self._save_chat_metadata(chat)

        return True

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and all its messages.

        Args:
            chat_id: Chat ID

        Returns:
            True if successful, False if chat not found
        """
        chat_dir = self.chats_dir / chat_id
        if not chat_dir.exists():
            return False

        # Delete all files in chat directory
        for file in chat_dir.iterdir():
            file.unlink()

        # Delete directory
        chat_dir.rmdir()
        return True

    def rename_chat(self, chat_id: str, new_name: str) -> bool:
        """
        Rename a chat.

        Args:
            chat_id: Chat ID
            new_name: New chat name

        Returns:
            True if successful, False if chat not found
        """
        chat, _ = self.get_chat(chat_id)
        if not chat:
            return False

        chat.name = new_name
        chat.updated_at = datetime.now().isoformat()
        self._save_chat_metadata(chat)
        return True

    def update_gemini_history(self, chat_id: str, history: List[Dict[str, Any]]) -> bool:
        """
        Update Gemini chat history for a chat.

        Args:
            chat_id: Chat ID
            history: Gemini chat history

        Returns:
            True if successful, False if chat not found
        """
        chat, _ = self.get_chat(chat_id)
        if not chat:
            return False

        chat.gemini_chat_history = history
        chat.updated_at = datetime.now().isoformat()
        self._save_chat_metadata(chat)
        return True

    def _save_chat_metadata(self, chat: Chat):
        """Save chat metadata to disk."""
        chat_dir = self.chats_dir / chat.id
        chat_dir.mkdir(exist_ok=True)

        metadata_file = chat_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(chat.to_dict(), f, indent=2)
