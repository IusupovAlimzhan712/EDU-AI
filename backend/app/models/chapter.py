"""
Chapter entity - Table 4.33 in FYP1 report.

Composite primary key (form_level, chapter_id) as specified in the
ERD's 3NF normalization step.
"""
from ..extensions import db


class Chapter(db.Model):
    __tablename__ = 'chapter'

    form_level = db.Column('formLevel', db.Integer, primary_key=True)
    chapter_id = db.Column('chapterId', db.Integer, primary_key=True)
    chapter_name = db.Column('chapterName', db.String(255), nullable=False)

    __table_args__ = (
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_chapter_form_level'),
        db.CheckConstraint('chapterId >= 1', name='ck_chapter_id_positive'),
    )

    # --- Relationships ---
    topics = db.relationship(
        'Topic',
        primaryjoin=(
            "and_(Topic.form_level == Chapter.form_level, "
            "Topic.chapter_id == Chapter.chapter_id)"
        ),
        foreign_keys='[Topic.form_level, Topic.chapter_id]',
        back_populates='chapter',
        viewonly=True,
    )

    def to_dict(self) -> dict:
        return {
            'formLevel': self.form_level,
            'chapterId': self.chapter_id,
            'chapterName': self.chapter_name,
        }

    def __repr__(self) -> str:
        return f'<Chapter F{self.form_level}-{self.chapter_id} {self.chapter_name}>'
