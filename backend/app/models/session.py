from datetime import datetime, timezone

from ..extensions import db


class Session(db.Model):
    __tablename__ = 'session'

    session_id = db.Column('sessionId', db.String(128), primary_key=True)
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        'createdAt', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_activity = db.Column(
        'lastActivity', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_active = db.Column('isActive', db.Boolean, nullable=False, default=True)

    # --- Relationships ---
    student = db.relationship('Student', back_populates='sessions')

    def deactivate(self):
        """Mark this session inactive on logout (UC 4.3.6)."""
        self.is_active = False

    def __repr__(self) -> str:
        return f'<Session {self.session_id[:8]}... student={self.student_id}>'
