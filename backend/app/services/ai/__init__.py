"""
AI services package.

Strategy pattern (FYP1 Section 5.3.3):
  IQuestionGenerator (interface)
      └─ LlmQuestionGenerator   (Quiz MCQ generation)
  IChatTutor (interface)
      └─ LlmChatTutor           (AI Tutor chat)

Plus ContentValidator (MCQ) and TutorValidator (chat) for output safety.
"""
from .base import IQuestionGenerator, GeneratedQuestion
from .llm_generator import LlmQuestionGenerator
from .content_validator import ContentValidator
from .language_normalizer import normalize as normalize_language
from .question_classifier import classify_question, is_social_message
from .tutor_base import IChatTutor, ChatTurn, TutorResponse
from .llm_tutor import LlmChatTutor
from .tutor_validator import TutorValidator
from .entity_gate import (
    check_entity_gate, detect_expected_entity_type,
    context_has_entity, UNCERTAINTY_RESPONSE,
)
from .embedding_service import (
    embed_text, embed_texts, cosine_similarity,
    serialize_embedding, deserialize_embedding,
    EMBEDDING_MODEL, EMBEDDING_DIM,
)

__all__ = [
    'IQuestionGenerator', 'GeneratedQuestion',
    'LlmQuestionGenerator', 'ContentValidator',
    'normalize_language', 'classify_question', 'is_social_message',
    'IChatTutor', 'ChatTurn', 'TutorResponse',
    'LlmChatTutor', 'TutorValidator',
    'check_entity_gate', 'detect_expected_entity_type',
    'context_has_entity', 'UNCERTAINTY_RESPONSE',
    'embed_text', 'embed_texts', 'cosine_similarity',
    'serialize_embedding', 'deserialize_embedding',
    'EMBEDDING_MODEL', 'EMBEDDING_DIM',
]