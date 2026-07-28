from datetime import datetime, date, timezone

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
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    current_streak = db.Column(
        'currentStreak', db.Integer, nullable=False, default=0, server_default='0'
    )
    last_study_date = db.Column('lastStudyDate', db.Date, nullable=True)

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
            'currentStreak': self.current_streak or 0,
            'lastStudyDate': self.last_study_date.isoformat() if self.last_study_date else None,
        }

    def __repr__(self) -> str:
        return f'<LearningProgress student={self.student_id}>'
