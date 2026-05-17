"""ChatRepository — data access for conversations and messages."""
from typing import List, Optional

from ..extensions import db
from ..models import ChatConversation, ChatMessage


class ChatRepository:

    @staticmethod
    def get_or_create_conversation(student_id: int, topic_id: int) -> ChatConversation:
        conv = db.session.query(ChatConversation).filter_by(
            student_id=student_id, topic_id=topic_id
        ).first()
        if conv:
            return conv
        conv = ChatConversation(student_id=student_id, topic_id=topic_id)
        db.session.add(conv)
        db.session.flush()
        return conv

    @staticmethod
    def get_conversation(student_id: int, topic_id: int) -> Optional[ChatConversation]:
        return db.session.query(ChatConversation).filter_by(
            student_id=student_id, topic_id=topic_id
        ).first()

    @staticmethod
    def list_messages(conversation_id: int) -> List[ChatMessage]:
        return db.session.query(ChatMessage).filter_by(
            conversation_id=conversation_id
        ).order_by(ChatMessage.created_at, ChatMessage.message_id).all()

    @staticmethod
    def add_message(
        conversation_id: int,
        role: str,
        content: str,
        source_page_start: Optional[int] = None,
        source_page_end: Optional[int] = None,
        validation_status: str = 'na',
        validation_warning: Optional[str] = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            source_page_start=source_page_start,
            source_page_end=source_page_end,
            validation_status=validation_status,
            validation_warning=validation_warning,
        )
        db.session.add(msg)
        db.session.flush()
        return msg

    @staticmethod
    def delete_conversation(student_id: int, topic_id: int) -> bool:
        conv = ChatRepository.get_conversation(student_id, topic_id)
        if not conv:
            return False
        db.session.delete(conv)
        db.session.flush()
        return True