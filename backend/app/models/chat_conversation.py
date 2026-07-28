from datetime import datetime, timezone
from ..extensions import db


class ChatConversation(db.Model):
    __tablename__ = 'chat_conversation'

    conversation_id = db.Column(
        'conversationId', db.Integer, primary_key=True, autoincrement=True
    )
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    topic_id = db.Column(
        'topicId',
        db.Integer,
        db.ForeignKey('topic.topicId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        'createdAt', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        'updatedAt', db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            'studentId', 'topicId', name='uq_chat_student_topic'
        ),
    )

    messages = db.relationship(
        'ChatMessage',
        back_populates='conversation',
        cascade='all, delete-orphan',
        order_by='ChatMessage.created_at',
    )

    def to_dict(self) -> dict:
        return {
            'conversationId': self.conversation_id,
            'studentId': self.student_id,
            'topicId': self.topic_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'messages': [m.to_dict() for m in self.messages],
        }