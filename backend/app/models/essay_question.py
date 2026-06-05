"""
EssayQuestion — a persistent SPM Sejarah Kertas 2 practice question.

Each row is a complete package: question text + unified F/H/C marking scheme tree
+ model answer, generated together so the scheme is the source of truth for grading.

question_type:
  'struktur' — Bahagian A sub-parts; graded by F/H/C code matching (Mana-mana N×1m)
  'esei'     — Bahagian B part (c); graded holistically via Aras 1-4 rubric
"""
from datetime import datetime

from ..extensions import db


class EssayQuestion(db.Model):
    __tablename__ = 'essay_question'

    question_id = db.Column(
        'questionId', db.Integer, primary_key=True, autoincrement=True
    )
    question_text = db.Column('questionText', db.Text, nullable=False)
    question_type = db.Column('questionType', db.String(16), nullable=False)
    form_level = db.Column('formLevel', db.Integer, nullable=False, index=True)
    chapter_id = db.Column('chapterId', db.Integer, nullable=False, index=True)
    sub_question = db.Column('subQuestion', db.String(8), nullable=True)
    max_marks = db.Column('maxMarks', db.Integer, nullable=False)
    difficulty = db.Column(db.String(16), nullable=False, default='medium')
    marking_scheme_json = db.Column('markingSchemeJson', db.JSON, nullable=False)
    model_answer = db.Column('modelAnswer', db.Text, nullable=False)
    created_at = db.Column('createdAt', db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_eq_form_level'),
        db.CheckConstraint(
            "questionType IN ('struktur', 'esei')", name='ck_eq_question_type'
        ),
        db.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')", name='ck_eq_difficulty'
        ),
        db.ForeignKeyConstraint(
            ['formLevel', 'chapterId'],
            ['chapter.formLevel', 'chapter.chapterId'],
            name='fk_eq_chapter',
            ondelete='CASCADE',
        ),
    )

    chapter = db.relationship(
        'Chapter',
        foreign_keys='[EssayQuestion.form_level, EssayQuestion.chapter_id]',
        primaryjoin=(
            "and_(EssayQuestion.form_level == Chapter.form_level, "
            "EssayQuestion.chapter_id == Chapter.chapter_id)"
        ),
        viewonly=True,
    )
    attempts = db.relationship(
        'EssayAttempt', back_populates='question', cascade='all, delete-orphan'
    )

    def to_summary_dict(self) -> dict:
        return {
            'questionId': self.question_id,
            'questionText': self.question_text,
            'questionType': self.question_type,
            'formLevel': self.form_level,
            'chapterId': self.chapter_id,
            'chapterName': self.chapter.chapter_name if self.chapter else '',
            'subQuestion': self.sub_question,
            'maxMarks': self.max_marks,
            'difficulty': self.difficulty,
        }

    def to_dict(self) -> dict:
        d = self.to_summary_dict()
        d['markingScheme'] = self.marking_scheme_json
        d['modelAnswer'] = self.model_answer
        d['createdAt'] = self.created_at.isoformat() if self.created_at else None
        return d
