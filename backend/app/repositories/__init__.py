"""Repository pattern (Data Access layer)."""
from .student_repository import StudentRepository
from .session_repository import SessionRepository
from .learning_progress_repository import LearningProgressRepository
from .topic_repository import TopicRepository
from .topic_page_repository import TopicPageRepository
from .chapter_repository import ChapterRepository
from .password_reset_repository import PasswordResetRepository
from .quiz_repository import QuizRepository
from .quiz_attempt_repository import QuizAttemptRepository
from .attempt_question_repository import AttemptQuestionRepository
from .chat_repository import ChatRepository

__all__ = [
    'StudentRepository', 'SessionRepository', 'LearningProgressRepository',
    'TopicRepository', 'TopicPageRepository', 'ChapterRepository',
    'PasswordResetRepository',
    'QuizRepository', 'QuizAttemptRepository', 'AttemptQuestionRepository', 'ChatRepository',
]