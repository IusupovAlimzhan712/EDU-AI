"""
TopicPage entity.

One row per page of each Topic's PDF. The AI tutor uses these rows for
page-precise context (Phase 3); the quiz generator concatenates them for
chapter-wide context.

Populated by `scripts/ingest_pdf.py` after a PDF is dropped into
backend/static/pdfs/.
"""
from ..extensions import db


class TopicPage(db.Model):
    __tablename__ = 'topic_page'

    topic_page_id = db.Column(
        'topicPageId', db.Integer, primary_key=True, autoincrement=True
    )
    topic_id = db.Column(
        'topicId',
        db.Integer,
        db.ForeignKey('topic.topicId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    page_number = db.Column('pageNumber', db.Integer, nullable=False)
    text_content = db.Column('textContent', db.Text, nullable=False, default='')
    word_count = db.Column('wordCount', db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('topicId', 'pageNumber', name='uq_topic_page'),
        db.CheckConstraint('pageNumber >= 1', name='ck_page_number_positive'),
    )

    topic = db.relationship('Topic', back_populates='pages')

    def to_dict(self) -> dict:
        return {
            'topicPageId': self.topic_page_id,
            'topicId': self.topic_id,
            'pageNumber': self.page_number,
            'textContent': self.text_content,
            'wordCount': self.word_count,
        }

    def __repr__(self) -> str:
        return f'<TopicPage topic={self.topic_id} page={self.page_number}>'