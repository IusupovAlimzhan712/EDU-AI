"""
Session entity - Table 4.31 in FYP1 report.

Each successful login creates a Session row. `session_id` stores the JWT
identifier (jti) so we can invalidate individual tokens on logout.
"""
from datetime import datetime

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
        'createdAt', db.DateTime, nullable=False, default=datetime.utcnow
    )
    last_activity = db.Column(
        'lastActivity', db.DateTime, nullable=False, default=datetime.utcnow
    )
    is_active = db.Column('isActive', db.Boolean, nullable=False, default=True)

    # --- Relationships ---
    student = db.relationship('Student', back_populates='sessions')

    def touch(self):
        """Update lastActivity to now (UC 4.3.5)."""
        self.last_activity = datetime.utcnow()

    def deactivate(self):
        """Mark this session inactive on logout (UC 4.3.6)."""
        self.is_active = False

    def to_dict(self) -> dict:
        return {
            'sessionId': self.session_id,
            'studentId': self.student_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastActivity': self.last_activity.isoformat() if self.last_activity else None,
            'isActive': self.is_active,
        }

    def __repr__(self) -> str:
        return f'<Session {self.session_id[:8]}... student={self.student_id}>'
