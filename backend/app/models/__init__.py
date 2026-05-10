"""
Entity classes (Entity layer of ECB).

All SQLAlchemy models are imported here so Flask-Migrate can discover them
via the single import `from app import models`.

Mirrors the Data Dictionary in Section 4.6.1 of the FYP1 report.
"""
from .student import Student
from .session import Session
from .learning_progress import LearningProgress
from .chapter import Chapter
from .topic import Topic
from .completed_topic import CompletedTopic
from .bookmarked_topic import BookmarkedTopic
from .password_reset_token import PasswordResetToken

__all__ = [
    'Student',
    'Session',
    'LearningProgress',
    'Chapter',
    'Topic',
    'CompletedTopic',
    'BookmarkedTopic',
    'PasswordResetToken',
]
