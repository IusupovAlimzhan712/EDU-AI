"""
AttemptQuestion — per-attempt snapshot of an AI-generated MCQ.

Each QuizAttempt owns its own set of questions. This means:
  - Two students taking the same Bab quiz get DIFFERENT questions.
  - The student's review screen always shows the exact questions they
    answered — even if they regenerate the quiz later.
  - History is auditable: every attempt's questions are preserved forever.
"""
from ..extensions import db


class AttemptQuestion(db.Model):
    __tablename__ = 'attempt_question'

    attempt_question_id = db.Column(
        'attemptQuestionId', db.Integer, primary_key=True, autoincrement=True
    )
    attempt_id = db.Column(
        'attemptId',
        db.Integer,
        db.ForeignKey('quiz_attempt.attemptId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    order_index = db.Column('orderIndex', db.Integer, nullable=False)
    stem = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # length 4
    correct_index = db.Column('correctIndex', db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        db.UniqueConstraint('attemptId', 'orderIndex', name='uq_attempt_question_order'),
        db.CheckConstraint('correctIndex BETWEEN 0 AND 3', name='ck_aq_correct_idx'),
    )

    attempt = db.relationship('QuizAttempt', back_populates='attempt_questions')
    answer = db.relationship(
        'AttemptAnswer', back_populates='attempt_question',
        uselist=False, cascade='all, delete-orphan',
    )

    def to_student_dict(self) -> dict:
        from ..services.ai.quiz_difficulty_classifier import classify_difficulty
        return {
            'attemptQuestionId': self.attempt_question_id,
            'orderIndex': self.order_index,
            'stem': self.stem,
            'options': self.options or [],
            'points': self.points,
            'difficulty': classify_difficulty(self.stem or ''),
        }

    def to_review_dict(self) -> dict:
        d = self.to_student_dict()
        d['correctIndex'] = self.correct_index
        d['explanation'] = self.explanation
        return d