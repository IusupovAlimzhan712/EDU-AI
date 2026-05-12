"""
Repository pattern (Data Access layer).
"""
from .student_repository import StudentRepository
from .session_repository import SessionRepository
from .learning_progress_repository import LearningProgressRepository
from .topic_repository import TopicRepository
from .topic_page_repository import TopicPageRepository
from .chapter_repository import ChapterRepository
from .password_reset_repository import PasswordResetRepository

__all__ = [
    'StudentRepository',
    'SessionRepository',
    'LearningProgressRepository',
    'TopicRepository',
    'TopicPageRepository',
    'ChapterRepository',
    'PasswordResetRepository',
]