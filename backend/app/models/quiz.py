"""
Quiz entity — Section 4.4 of FYP1 report.

Step 5 change: Quiz is now a TEMPLATE (scope, title, difficulty target).
Questions live per-attempt in AttemptQuestion. Quiz no longer has
questions of its own.
"""
from datetime import datetime

from ..extensions import db


class Quiz(db.Model):
    __tablename__ = 'quiz'

    quiz_id = db.Column('quizId', db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    form_level = db.Column('formLevel', db.Integer, nullable=False)
    chapter_id = db.Column('chapterId', db.Integer, nullable=True)
    scope = db.Column(db.String(16), nullable=False)
    source = db.Column(db.String(16), nullable=False, default='ai')
    difficulty = db.Column(db.String(16), nullable=True)

    # How many questions to generate per attempt
    default_question_count = db.Column(
        'defaultQuestionCount', db.Integer, nullable=False, default=10
    )

    created_at = db.Column('createdAt', db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        'updatedAt', db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_quiz_form_level'),
        db.CheckConstraint("scope IN ('bab', 'form')", name='ck_quiz_scope'),
        db.UniqueConstraint('formLevel', 'chapterId', 'scope', name='uq_quiz_scope'),
    )

    attempts = db.relationship(
        'QuizAttempt', back_populates='quiz', cascade='all, delete-orphan'
    )

    def to_summary_dict(self) -> dict:
        return {
            'quizId': self.quiz_id,
            'title': self.title,
            'formLevel': self.form_level,
            'chapterId': self.chapter_id,
            'scope': self.scope,
            'source': self.source,
            'difficulty': self.difficulty,
            'defaultQuestionCount': self.default_question_count,
        }

    def to_dict(self) -> dict:
        d = self.to_summary_dict()
        d['createdAt'] = self.created_at.isoformat() if self.created_at else None
        d['updatedAt'] = self.updated_at.isoformat() if self.updated_at else None
        return d