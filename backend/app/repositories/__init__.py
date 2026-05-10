"""
Repository pattern (Data Access layer).

Each repository wraps SQLAlchemy queries for one entity. Services depend
on repositories — never on `db.session` directly — which makes services
trivially testable (swap a repo for an in-memory fake).

This matches the "Repository Pattern" call-out in Section 5.3.3 of the
FYP1 report.
"""
from .student_repository import StudentRepository
from .session_repository import SessionRepository
from .learning_progress_repository import LearningProgressRepository
from .topic_repository import TopicRepository
from .chapter_repository import ChapterRepository
from .password_reset_repository import PasswordResetRepository

__all__ = [
    'StudentRepository',
    'SessionRepository',
    'LearningProgressRepository',
    'TopicRepository',
    'ChapterRepository',
    'PasswordResetRepository',
]
