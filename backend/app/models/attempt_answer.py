from datetime import datetime, timezone

from ..extensions import db


class AttemptAnswer(db.Model):
    __tablename__ = 'attempt_answer'

    attempt_id = db.Column(
        'attemptId',
        db.Integer,
        db.ForeignKey('quiz_attempt.attemptId', ondelete='CASCADE'),
        primary_key=True,
    )
    attempt_question_id = db.Column(
        'attemptQuestionId',
        db.Integer,
        db.ForeignKey('attempt_question.attemptQuestionId', ondelete='CASCADE'),
        primary_key=True,
    )

    selected_index = db.Column('selectedIndex', db.Integer, nullable=True)
    is_correct = db.Column('isCorrect', db.Boolean, nullable=True)

    answered_at = db.Column(
        'answeredAt',
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            'selectedIndex IS NULL OR selectedIndex BETWEEN 0 AND 3',
            name='ck_answer_idx',
        ),
    )

    attempt = db.relationship('QuizAttempt', back_populates='answers')
    attempt_question = db.relationship('AttemptQuestion', back_populates='answer')

    def to_dict(self) -> dict:
        return {
            'attemptId': self.attempt_id,
            'attemptQuestionId': self.attempt_question_id,
            'selectedIndex': self.selected_index,
            'isCorrect': self.is_correct,
            'answeredAt': self.answered_at.isoformat() if self.answered_at else None,
        }