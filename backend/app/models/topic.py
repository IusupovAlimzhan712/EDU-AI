"""
Topic entity - Table 4.34 in FYP1 report.

References Chapter via (form_level, chapter_id) composite FK.
"""
from ..extensions import db


class Topic(db.Model):
    __tablename__ = 'topic'

    topic_id = db.Column('topicId', db.Integer, primary_key=True, autoincrement=True)
    form_level = db.Column('formLevel', db.Integer, nullable=False)
    chapter_id = db.Column('chapterId', db.Integer, nullable=False)
    topic_name = db.Column('topicName', db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Optional metadata used by the frontend topic cards (duration label,
    # PDF reference for the embedded viewer). Not in the data dictionary
    # but harmless to include; if you prefer to be strict, remove and
    # update the seed file.
    estimated_duration_minutes = db.Column(
        'estimatedDurationMinutes', db.Integer, nullable=True
    )
    pdf_reference = db.Column('pdfReference', db.String(500), nullable=True)

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
    completions = db.relationship(
        'CompletedTopic', back_populates='topic', cascade='all, delete-orphan'
    )
    bookmarks = db.relationship(
        'BookmarkedTopic', back_populates='topic', cascade='all, delete-orphan'
    )

    def to_summary_dict(self) -> dict:
        """Lightweight view for list endpoints (no full content)."""
        return {
            'topicId': self.topic_id,
            'formLevel': self.form_level,
            'chapterId': self.chapter_id,
            'topicName': self.topic_name,
            'chapterName': self.chapter.chapter_name if self.chapter else None,
            'estimatedDurationMinutes': self.estimated_duration_minutes,
        }

    def to_dict(self) -> dict:
        """Full detail view including content."""
        d = self.to_summary_dict()
        d['content'] = self.content
        d['pdfReference'] = self.pdf_reference
        return d

    def __repr__(self) -> str:
        return f'<Topic {self.topic_id} F{self.form_level}-C{self.chapter_id} {self.topic_name}>'
