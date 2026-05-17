"""
AI services package.

Strategy pattern (FYP1 Section 5.3.3):
  IQuestionGenerator (interface)
      └─ OllamaQuestionGenerator   (Quiz MCQ generation)
  IChatTutor (interface)
      └─ OllamaChatTutor           (AI Tutor chat)

Plus ContentValidator (MCQ) and TutorValidator (chat) for output safety.
"""
from .base import IQuestionGenerator, GeneratedQuestion
from .ollama_generator import OllamaQuestionGenerator
from .content_validator import ContentValidator
from .language_normalizer import normalize as normalize_language
from .question_classifier import classify_question
from .tutor_base import IChatTutor, ChatTurn, TutorResponse
from .ollama_tutor import OllamaChatTutor
from .tutor_validator import TutorValidator
from .entity_gate import (
    check_entity_gate, detect_expected_entity_type,
    context_has_entity, UNCERTAINTY_RESPONSE,
)

__all__ = [
    'IQuestionGenerator', 'GeneratedQuestion',
    'OllamaQuestionGenerator', 'ContentValidator',
    'normalize_language', 'classify_question',
    'IChatTutor', 'ChatTurn', 'TutorResponse',
    'OllamaChatTutor', 'TutorValidator',
    'check_entity_gate', 'detect_expected_entity_type',
    'context_has_entity', 'UNCERTAINTY_RESPONSE',
]