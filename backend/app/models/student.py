from datetime import datetime, date, timezone

from ..extensions import db


class Student(db.Model):
    __tablename__ = 'student'

    student_id = db.Column('studentId', db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column('passwordHash', db.String(255), nullable=False)
    full_name = db.Column('fullName', db.String(100), nullable=False)
    form_level = db.Column('formLevel', db.Integer, nullable=False)
    registration_date = db.Column(
        'registrationDate', db.Date, nullable=False, default=date.today
    )

    # Learning preferences — nullable so existing rows default to None (resolved at use time)
    quiz_difficulty = db.Column('quizDifficulty', db.String(16), nullable=True)
    questions_per_quiz = db.Column('questionsPerQuiz', db.Integer, nullable=True)

    # Brute-force protection (UC-F1.2 E1)
    failed_attempts = db.Column('failedAttempts', db.Integer, nullable=False,
                                default=0, server_default='0')
    locked_until = db.Column('lockedUntil', db.DateTime, nullable=True)

    def is_locked(self) -> bool:
        """Return True if the account is currently within a lock window."""
        if not self.locked_until:
            return False
        lu = self.locked_until
        if lu.tzinfo is None:
            lu = lu.replace(tzinfo=timezone.utc)
        return lu > datetime.now(timezone.utc)

    __table_args__ = (
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_student_form_level'),
        db.CheckConstraint(
            "quizDifficulty IS NULL OR quizDifficulty IN ('easy', 'medium', 'hard')",
            name='ck_student_quiz_difficulty',
        ),
    )

    # --- Relationships ---
    sessions = db.relationship(
        'Session', back_populates='student', cascade='all, delete-orphan'
    )
    learning_progress = db.relationship(
        'LearningProgress',
        back_populates='student',
        uselist=False,
        cascade='all, delete-orphan',
    )
    reset_tokens = db.relationship(
        'PasswordResetToken', back_populates='student', cascade='all, delete-orphan'
    )

    def to_dict(self) -> dict:
        """Public representation. NEVER includes password_hash."""
        return {
            'studentId': self.student_id,
            'email': self.email,
            'fullName': self.full_name,
            'formLevel': self.form_level,
            'registrationDate': self.registration_date.isoformat()
                if self.registration_date else None,
            'quizDifficulty': self.quiz_difficulty,
            'questionsPerQuiz': self.questions_per_quiz,
        }

    def __repr__(self) -> str:
        return f'<Student {self.student_id} {self.email}>'
