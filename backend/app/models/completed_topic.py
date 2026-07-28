from datetime import datetime, timezone

from ..extensions import db


class CompletedTopic(db.Model):
    __tablename__ = 'completed_topic'

    progress_id = db.Column(
        'progressId',
        db.Integer,
        db.ForeignKey('learning_progress.progressId', ondelete='CASCADE'),
        primary_key=True,
    )
    topic_id = db.Column(
        'topicId',
        db.Integer,
        db.ForeignKey('topic.topicId', ondelete='CASCADE'),
        primary_key=True,
    )
    completed_at = db.Column(
        'completedAt', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    progress = db.relationship('LearningProgress', back_populates='completed_topics')
    topic = db.relationship('Topic', back_populates='completions')

    def to_dict(self) -> dict:
        return {
            'progressId': self.progress_id,
            'topicId': self.topic_id,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }
