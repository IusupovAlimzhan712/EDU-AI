"""StudentRepository — all DB access for Student rows."""
from typing import Optional

from ..extensions import db
from ..models import Student


class StudentRepository:

    @staticmethod
    def get_by_id(student_id: int) -> Optional[Student]:
        return db.session.get(Student, student_id)

    @staticmethod
    def get_by_email(email: str) -> Optional[Student]:
        return db.session.query(Student).filter(
            db.func.lower(Student.email) == email.lower()
        ).first()

    @staticmethod
    def email_exists(email: str) -> bool:
        return StudentRepository.get_by_email(email) is not None

    @staticmethod
    def create(
        email: str,
        password_hash: str,
        full_name: str,
        form_level: int,
    ) -> Student:
        student = Student(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            form_level=form_level,
        )
        db.session.add(student)
        db.session.flush()  # populate student_id without committing
        return student

    @staticmethod
    def update(student: Student, **fields) -> Student:
        for key, value in fields.items():
            if hasattr(student, key) and value is not None:
                setattr(student, key, value)
        db.session.flush()
        return student

    @staticmethod
    def delete(student: Student) -> None:
        db.session.delete(student)

    @staticmethod
    def commit() -> None:
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        db.session.rollback()
