"""
CompletedTopic junction table - Table 4.35 in FYP1 report.

Implements the many-to-many between LearningProgress and Topic for topic
completion tracking (1NF normalization).
"""
from datetime import datetime

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
        'completedAt', db.DateTime, nullable=False, default=datetime.utcnow
    )

    progress = db.relationship('LearningProgress', back_populates='completed_topics')
    topic = db.relationship('Topic', back_populates='completions')

    def to_dict(self) -> dict:
        return {
            'progressId': self.progress_id,
            'topicId': self.topic_id,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }
