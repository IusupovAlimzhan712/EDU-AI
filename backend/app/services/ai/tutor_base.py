"""
Interface for chat tutors (Strategy pattern, FYP1 Section 5.3.3).

Mirrors IQuestionGenerator but for free-form chat responses.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


@dataclass
class ChatTurn:
    """A single turn in the conversation history fed to the LLM."""
    role: str         # 'user' or 'assistant'
    content: str


@dataclass
class TutorResponse:
    """Final, fully-validated response shown to the student."""
    content: str
    validation_status: str       # 'ok' or 'warned'
    validation_warning: Optional[str] = None


class IChatTutor(ABC):

    @abstractmethod
    def stream_reply(
        self,
        question: str,
        page_context: str,
        chapter_name: str,
        history: List[ChatTurn],
    ) -> Iterator[dict]:
        """Yield SSE events: 'token' (partial), 'final' (complete + validated), 'error'."""
        raise NotImplementedError