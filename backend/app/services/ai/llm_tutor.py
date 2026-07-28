"""
GPT-4o-mini implementation of IChatTutor — streams tokens with validation.

Strategy:
  1. Classify question type (factual / comparison / kbat).
  2. Build mode-appropriate prompt + set dynamic max_tokens cap.
  3. Stream tokens from OpenAI; accumulate into a buffer.
  4. Yield 'token' events in real time (live SSE feel).
  5. Normalize the complete buffer (Indonesian → BM, Unicode fix).
  6. Validate; if failed AND retries remain, regenerate.
  7. Yield 'final' event with validated, normalized response.
"""
import logging
from typing import Iterator, List

from langchain_openai import ChatOpenAI

from .language_normalizer import normalize
from .llm_config import get_openai_api_key, get_openai_model, get_openai_timeout
from .question_classifier import MODE_TOKENS
from .tutor_base import IChatTutor, ChatTurn
from .tutor_prompts import build_tutor_messages, build_general_tutor_messages, build_social_messages
from .tutor_validator import TutorValidator


logger = logging.getLogger(__name__)

_DEFAULT_TOKENS = 400


class LlmChatTutor(IChatTutor):

    MAX_RETRIES = 1  # 1 initial + 1 retry = 2 total attempts

    def _make_llm(self, mode: str = 'kbat') -> ChatOpenAI:
        """Create a GPT-4o-mini LLM instance with the correct token cap for *mode*."""
        return ChatOpenAI(
            api_key=get_openai_api_key(),
            model=get_openai_model(),
            temperature=0.4,
            max_tokens=MODE_TOKENS.get(mode, _DEFAULT_TOKENS),
            timeout=get_openai_timeout(),
        )

    def stream_reply(
        self,
        question: str,
        page_context: str,
        chapter_name: str,
        history: List[ChatTurn],
        mode: str = 'kbat',
        low_confidence: bool = False,
        current_page: int = 0,
        page_referential: bool = False,
    ) -> Iterator[dict]:
        return self._stream(
            question=question,
            page_context=page_context,
            history=history,
            use_general_prompt=False,
            chapter_name=chapter_name,
            mode=mode,
            low_confidence=low_confidence,
            current_page=current_page,
            page_referential=page_referential,
        )

    def stream_social_reply(self, question: str) -> Iterator[dict]:
        """Handle casual/social messages — no KB retrieval, warm brief response."""
        llm = ChatOpenAI(
            api_key=get_openai_api_key(),
            model=get_openai_model(),
            temperature=0.7,
            max_tokens=120,
            timeout=get_openai_timeout(),
        )
        messages = build_social_messages(question)
        buffer = ''
        try:
            for chunk in llm.stream(messages):
                piece = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if not piece:
                    continue
                buffer += piece
                yield {'event': 'token', 'chunk': piece}
        except Exception as exc:
            logger.warning('Social reply streaming failed: %s', exc)
            buffer = 'Hai! Saya sedia membantu anda belajar Sejarah. Ada soalan?'
            yield {'event': 'token', 'chunk': buffer}

        yield {
            'event': 'final',
            'content': buffer or 'Hai! Saya sedia membantu anda belajar Sejarah. Ada soalan?',
            'validation_status': 'ok',
            'validation_warning': None,
        }

    def stream_general_reply(
        self,
        question: str,
        page_context: str,
        history: List[ChatTurn],
        mode: str = 'kbat',
        low_confidence: bool = False,
    ) -> Iterator[dict]:
        return self._stream(
            question=question,
            page_context=page_context,
            history=history,
            use_general_prompt=True,
            mode=mode,
            low_confidence=low_confidence,
        )

    def _stream(
        self,
        question: str,
        page_context: str,
        history: List[ChatTurn],
        use_general_prompt: bool = False,
        chapter_name: str = '',
        mode: str = 'kbat',
        low_confidence: bool = False,
        current_page: int = 0,
        page_referential: bool = False,
    ) -> Iterator[dict]:
        llm = self._make_llm(mode)
        last_warning = None
        last_buffer = ''

        for attempt in range(1, self.MAX_RETRIES + 2):
            if use_general_prompt:
                messages = build_general_tutor_messages(
                    page_context=page_context,
                    question=question,
                    history=history,
                    mode=mode,
                    low_confidence=low_confidence,
                )
            else:
                messages = build_tutor_messages(
                    chapter_name=chapter_name,
                    page_context=page_context,
                    question=question,
                    history=history,
                    mode=mode,
                    low_confidence=low_confidence,
                    current_page=current_page,
                    page_referential=page_referential,
                )

            buffer = ''
            try:
                for chunk in llm.stream(messages):
                    piece = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if not piece:
                        continue
                    buffer += piece
                    if attempt == 1:
                        yield {'event': 'token', 'chunk': piece}
            except Exception as exc:
                logger.warning('Tutor attempt %d streaming failed: %s', attempt, exc)
                last_warning = f'Ralat streaming: {exc}'
                continue

            # Normalize before validation: fix Unicode, replace Indonesian words
            buffer = normalize(buffer)
            status, warning = TutorValidator.validate(buffer, page_context)
            last_buffer = buffer
            last_warning = warning

            if status == 'ok':
                yield {
                    'event': 'final',
                    'content': buffer,
                    'validation_status': 'ok',
                    'validation_warning': None,
                }
                return

            if attempt <= self.MAX_RETRIES:
                logger.info(
                    'Tutor attempt %d flagged (%s); retrying silently.', attempt, warning
                )
                yield {'event': 'reset'}
                continue

        yield {
            'event': 'final',
            'content': last_buffer or 'Maaf, AI tidak dapat menjana jawapan pada masa ini.',
            'validation_status': 'warned',
            'validation_warning': last_warning or 'Jawapan tidak lulus pengesahan.',
        }
