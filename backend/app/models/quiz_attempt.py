from datetime import datetime, timezone

from ..extensions import db


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempt'

    attempt_id = db.Column(
        'attemptId', db.Integer, primary_key=True, autoincrement=True
    )
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    quiz_id = db.Column(
        'quizId',
        db.Integer,
        db.ForeignKey('quiz.quizId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    status = db.Column(db.String(16), nullable=False, default='in_progress')

    # AI generation lifecycle for this attempt
    # 'pending' -> 'generating' -> 'ready' -> (becomes irrelevant after submit)
    # 'failed'  -> generation hit a hard error
    generation_status = db.Column(
        'generationStatus', db.String(16), nullable=False, default='pending'
    )
    target_question_count = db.Column(
        'targetQuestionCount', db.Integer, nullable=False, default=10
    )
    # Snapshotted from student preference (or quiz template) at attempt creation.
    # None means medium (generator default). Stored so streaming uses the setting
    # that was active when the student pressed "Start", not a later change.
    difficulty_target = db.Column('difficultyTarget', db.String(16), nullable=True)

    started_at = db.Column(
        'startedAt', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    submitted_at = db.Column('submittedAt', db.DateTime, nullable=True)

    score = db.Column(db.Integer, nullable=True)
    max_score = db.Column('maxScore', db.Integer, nullable=True)
    correct_count = db.Column('correctCount', db.Integer, nullable=True)
    total_questions = db.Column('totalQuestions', db.Integer, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('in_progress', 'submitted')",
            name='ck_attempt_status',
        ),
        db.CheckConstraint(
            "generationStatus IN ('pending', 'generating', 'ready', 'failed')",
            name='ck_attempt_gen_status',
        ),
        db.CheckConstraint(
            "difficultyTarget IS NULL OR difficultyTarget IN ('easy', 'medium', 'hard')",
            name='ck_attempt_difficulty_target',
        ),
    )

    quiz = db.relationship('Quiz', back_populates='attempts')
    attempt_questions = db.relationship(
        'AttemptQuestion',
        back_populates='attempt',
        cascade='all, delete-orphan',
        order_by='AttemptQuestion.order_index',
    )
    answers = db.relationship(
        'AttemptAnswer',
        back_populates='attempt',
        cascade='all, delete-orphan',
    )

    def to_summary_dict(self) -> dict:
        percentage = None
        if self.max_score and self.max_score > 0 and self.score is not None:
            percentage = round((self.score / self.max_score) * 100, 2)
        return {
            'attemptId': self.attempt_id,
            'quizId': self.quiz_id,
            'status': self.status,
            'generationStatus': self.generation_status,
            'targetQuestionCount': self.target_question_count,
            'difficultyTarget': self.difficulty_target,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'submittedAt': self.submitted_at.isoformat()
                if self.submitted_at else None,
            'score': self.score,
            'maxScore': self.max_score,
            'correctCount': self.correct_count,
            'totalQuestions': self.total_questions,
            'percentage': percentage,
        }