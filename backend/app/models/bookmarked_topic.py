"""
BookmarkedTopic junction table - Table 4.36 in FYP1 report.
"""
from datetime import datetime

from ..extensions import db


class BookmarkedTopic(db.Model):
    __tablename__ = 'bookmarked_topic'

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
    bookmarked_at = db.Column(
        'bookmarkedAt', db.DateTime, nullable=False, default=datetime.utcnow
    )

    progress = db.relationship('LearningProgress', back_populates='bookmarked_topics')
    topic = db.relationship('Topic', back_populates='bookmarks')

    def to_dict(self) -> dict:
        return {
            'progressId': self.progress_id,
            'topicId': self.topic_id,
            'bookmarkedAt': self.bookmarked_at.isoformat() if self.bookmarked_at else None,
        }
