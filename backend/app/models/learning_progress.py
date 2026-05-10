"""
LearningProgress entity - Table 4.32 in FYP1 report.

One-to-one with Student. Auto-created when a Student registers (see
AccountService.register).
"""
from datetime import datetime

from ..extensions import db


class LearningProgress(db.Model):
    __tablename__ = 'learning_progress'

    progress_id = db.Column(
        'progressId', db.Integer, primary_key=True, autoincrement=True
    )
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        unique=True,  # one-to-one
    )
    last_updated = db.Column(
        'lastUpdated',
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # --- Relationships ---
    student = db.relationship('Student', back_populates='learning_progress')
    completed_topics = db.relationship(
        'CompletedTopic',
        back_populates='progress',
        cascade='all, delete-orphan',
    )
    bookmarked_topics = db.relationship(
        'BookmarkedTopic',
        back_populates='progress',
        cascade='all, delete-orphan',
    )

    def to_dict(self) -> dict:
        return {
            'progressId': self.progress_id,
            'studentId': self.student_id,
            'lastUpdated': self.last_updated.isoformat() if self.last_updated else None,
            'completedTopicsCount': len(self.completed_topics or []),
            'bookmarkedTopicsCount': len(self.bookmarked_topics or []),
        }

    def __repr__(self) -> str:
        return f'<LearningProgress student={self.student_id}>'
