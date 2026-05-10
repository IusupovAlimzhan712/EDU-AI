"""
Student entity - Table 4.30 in FYP1 report.

Extended with `full_name` and `form_level` to match what the frontend
Register form collects. These are documented in docs/DEVIATIONS.md.
"""
from datetime import datetime, date

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

    __table_args__ = (
        db.CheckConstraint('formLevel IN (4, 5)', name='ck_student_form_level'),
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
        }

    def __repr__(self) -> str:
        return f'<Student {self.student_id} {self.email}>'
