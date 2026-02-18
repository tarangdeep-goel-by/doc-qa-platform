"""Load and manage benchmark Q&A datasets for evaluation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class BenchmarkQuestion:
    """A single benchmark question with expected answer."""
    id: str
    question: str
    claude_answer: str
    difficulty: str = "medium"
    category: str = "general"
    expected_sources: List[str] = field(default_factory=list)
    requires_synthesis: bool = False
    requires_organization: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkQuestion":
        return cls(
            id=data["id"],
            question=data["question"],
            claude_answer=data["claude_answer"],
            difficulty=data.get("difficulty", "medium"),
            category=data.get("category", "general"),
            expected_sources=data.get("expected_sources", []),
            requires_synthesis=data.get("requires_synthesis", False),
            requires_organization=data.get("requires_organization", False),
        )


@dataclass
class BenchmarkDataset:
    """A complete benchmark dataset with metadata and questions."""
    dataset_name: str
    document: str
    questions: List[BenchmarkQuestion]
    version: str = "1.0"
    description: str = ""

    @classmethod
    def from_file(cls, path: str) -> "BenchmarkDataset":
        """Load dataset from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        questions = [BenchmarkQuestion.from_dict(q) for q in data["questions"]]

        return cls(
            dataset_name=data["dataset_name"],
            document=data["document"],
            questions=questions,
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
        )

    def filter_by_category(self, category: str) -> List[BenchmarkQuestion]:
        """Return questions matching a category."""
        return [q for q in self.questions if q.category == category]

    def filter_by_difficulty(self, difficulty: str) -> List[BenchmarkQuestion]:
        """Return questions matching a difficulty level."""
        return [q for q in self.questions if q.difficulty == difficulty]

    def get_question(self, question_id: str) -> Optional[BenchmarkQuestion]:
        """Get a specific question by ID."""
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

    @property
    def categories(self) -> List[str]:
        return sorted(set(q.category for q in self.questions))

    @property
    def difficulties(self) -> List[str]:
        return sorted(set(q.difficulty for q in self.questions))


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation."""
    id: str
    question: str
    claude_answer: str
    difficulty: str = "medium"
    category: str = "general"
    depends_on_context: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(
            id=data["id"],
            question=data["question"],
            claude_answer=data["claude_answer"],
            difficulty=data.get("difficulty", "medium"),
            category=data.get("category", "general"),
            depends_on_context=data.get("depends_on_context", False),
        )


@dataclass
class Conversation:
    """A multi-turn conversation with ordered turns."""
    id: str
    turns: List[ConversationTurn]
    doc_ids_hint: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        turns = [ConversationTurn.from_dict(t) for t in data["turns"]]
        return cls(
            id=data["id"],
            turns=turns,
            doc_ids_hint=data.get("doc_ids_hint", ""),
        )


@dataclass
class ConversationalDataset:
    """A benchmark dataset of multi-turn conversations."""
    dataset_name: str
    conversations: List[Conversation]
    version: str = "1.0"
    description: str = ""

    @classmethod
    def from_file(cls, path: str) -> "ConversationalDataset":
        """Load conversational dataset from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        conversations = [Conversation.from_dict(c) for c in data["conversations"]]

        return cls(
            dataset_name=data["dataset_name"],
            conversations=conversations,
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
        )

    @property
    def total_turns(self) -> int:
        return sum(len(c.turns) for c in self.conversations)


def detect_dataset_type(path: str) -> str:
    """Detect whether a dataset file is 'standalone' or 'conversational'."""
    with open(path, "r") as f:
        data = json.load(f)
    if "conversations" in data:
        return "conversational"
    return "standalone"
