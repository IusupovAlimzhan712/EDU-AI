"""
ChatMessage entity.

One turn in a ChatConversation. 'user' messages are from the student;
'assistant' messages are AI-generated tutor responses.

validation_status records whether the response passed our checks:
  - 'ok'        : validation passed cleanly
  - 'warned'    : validation found issues but the response was shown anyway
                  (after exhausting retries) — frontend displays a banner
  - 'rejected'  : not used (rejected responses aren't saved)
  - 'na'        : not applicable (user messages)
"""
from datetime import datetime
from ..extensions import db


class ChatMessage(db.Model):
    __tablename__ = 'chat_message'

    message_id = db.Column(
        'messageId', db.Integer, primary_key=True, autoincrement=True
    )
    conversation_id = db.Column(
        'conversationId',
        db.Integer,
        db.ForeignKey('chat_conversation.conversationId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(16), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)

    # Context the student was looking at when they sent this message.
    # Null for assistant rows.
    source_page_start = db.Column('sourcePageStart', db.Integer, nullable=True)
    source_page_end = db.Column('sourcePageEnd', db.Integer, nullable=True)

    validation_status = db.Column(
        'validationStatus', db.String(16), nullable=False, default='na'
    )
    validation_warning = db.Column(
        'validationWarning', db.String(255), nullable=True
    )

    created_at = db.Column(
        'createdAt', db.DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'assistant')", name='ck_chat_msg_role'),
        db.CheckConstraint(
            "validationStatus IN ('ok', 'warned', 'na')",
            name='ck_chat_msg_validation',
        ),
    )

    conversation = db.relationship('ChatConversation', back_populates='messages')

    def to_dict(self) -> dict:
        return {
            'messageId': self.message_id,
            'conversationId': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'sourcePageStart': self.source_page_start,
            'sourcePageEnd': self.source_page_end,
            'validationStatus': self.validation_status,
            'validationWarning': self.validation_warning,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }