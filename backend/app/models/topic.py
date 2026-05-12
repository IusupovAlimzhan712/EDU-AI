"""
Topic entity - Table 4.34 in FYP1 report.

Changed in Step 2:
  - Dropped `content TEXT` column (replaced by PDF + topic_page rows).
  - Added `pdf_path` and `total_pages` to support the PDF viewer.
"""
from ..extensions import db


class Topic(db.Model):
    __tablename__ = 'topic'

    topic_id = db.Column('topicId', db.Integer, primary_key=True, autoincrement=True)
    form_level = db.Column('formLevel', db.Integer, nullable=False)
    chapter_id = db.Column('chapterId', db.Integer, nullable=False)
    topic_name = db.Column('topicName', db.String(255), nullable=False)

    # PDF file location (relative to backend/static/pdfs/) and cached page count
    pdf_path = db.Column('pdfPath', db.String(500), nullable=True)
    total_pages = db.Column('totalPages', db.Integer, nullable=True, default=0)

    estimated_duration_minutes = db.Column(
        'estimatedDurationMinutes', db.Integer, nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            'formLevel', 'chapterId', 'topicName',
            name='uq_topic_form_chapter_name',
        ),
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_topic_form_level'),
        db.ForeignKeyConstraint(
            ['formLevel', 'chapterId'],
            ['chapter.formLevel', 'chapter.chapterId'],
            name='fk_topic_chapter',
        ),
    )

    # --- Relationships ---
    chapter = db.relationship(
        'Chapter',
        back_populates='topics',
        foreign_keys='[Topic.form_level, Topic.chapter_id]',
        viewonly=True,
    )
    pages = db.relationship(
        'TopicPage',
        back_populates='topic',
        cascade='all, delete-orphan',
        order_by='TopicPage.page_number',
    )
    completions = db.relationship(
        'CompletedTopic', back_populates='topic', cascade='all, delete-orphan'
    )
    bookmarks = db.relationship(
        'BookmarkedTopic', back_populates='topic', cascade='all, delete-orphan'
    )

    def to_summary_dict(self) -> dict:
        """Lightweight view for list endpoints."""
        return {
            'topicId': self.topic_id,
            'formLevel': self.form_level,
            'chapterId': self.chapter_id,
            'topicName': self.topic_name,
            'chapterName': self.chapter.chapter_name if self.chapter else None,
            'estimatedDurationMinutes': self.estimated_duration_minutes,
            'hasPdf': bool(self.pdf_path),
            'totalPages': self.total_pages or 0,
        }

    def to_dict(self) -> dict:
        """Full detail view."""
        d = self.to_summary_dict()
        d['pdfPath'] = self.pdf_path
        return d

    def __repr__(self) -> str:
        return f'<Topic {self.topic_id} F{self.form_level}-C{self.chapter_id} {self.topic_name}>'