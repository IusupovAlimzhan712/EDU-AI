"""
Ollama implementation of IQuestionGenerator.

Uses LangChain's ChatOllama wrapper. Generates one question per LLM call
so the frontend can stream results as they arrive.
"""
import json
import logging
from typing import Iterator, List

from langchain_ollama import ChatOllama

from .base import IQuestionGenerator, GeneratedQuestion
from .content_validator import ContentValidator
from .language_normalizer import normalize
from .llm_config import get_ollama_base_url, get_ollama_model, get_ollama_timeout
from .prompt_templates import (
    MCQ_SINGLE_PROMPT_BM,
    build_previous_questions_summary,
    pick_angle,
)
from .quiz_difficulty_classifier import classify_difficulty


logger = logging.getLogger(__name__)


class OllamaQuestionGenerator(IQuestionGenerator):

    MAX_RETRIES_PER_QUESTION = 3

    def __init__(self):
        self._llm = ChatOllama(
            base_url=get_ollama_base_url(),
            model=get_ollama_model(),
            temperature=0.65,        # reduced: less hallucination, still varied
            num_predict=512,         # plenty for one MCQ in JSON
            timeout=get_ollama_timeout(),
            format='json',           # Ollama's JSON mode — much more reliable
        )

    
    # Jaccard similarity threshold — stems above this are considered duplicates
    _DEDUP_THRESHOLD = 0.5

    def generate_stream(
        self,
        context: str,
        num_questions: int,
        language: str = 'bm',
    ) -> Iterator[GeneratedQuestion]:
        if language != 'bm':
            logger.warning(f"Language '{language}' not yet supported, falling back to BM.")

        max_context_chars = 8000
        ctx = context[:max_context_chars] if len(context) > max_context_chars else context

        produced: List[GeneratedQuestion] = []

        for i in range(num_questions):
            angle = pick_angle(i)
            q = self._generate_one_with_retries(
                ctx, [p.stem for p in produced], angle,
            )
            if q is None:
                logger.warning(
                    f'Skipping question {i+1}/{num_questions} after '
                    f'{self.MAX_RETRIES_PER_QUESTION} retries.'
                )
                continue
            # Deduplication — Jaccard similarity check against already-produced stems
            if self._is_duplicate(q.stem, [p.stem for p in produced]):
                logger.warning(f'Duplicate question detected, skipping: {q.stem[:60]}')
                continue
            produced.append(q)
            yield q

    def _is_duplicate(self, stem: str, previous_stems: List[str]) -> bool:
        """Return True if stem is too similar to any previously generated question."""
        from .content_validator import _jaccard
        stem_tokens = set(stem.lower().split())
        for prev in previous_stems:
            prev_tokens = set(prev.lower().split())
            union = stem_tokens | prev_tokens
            if not union:
                continue
            sim = len(stem_tokens & prev_tokens) / len(union)
            if sim >= self._DEDUP_THRESHOLD:
                return True
        return False



    # ---- internals ----
        
    def _generate_one_with_retries(
        self, context: str, previous_stems: List[str], angle: str,
    ) -> GeneratedQuestion | None:
        for attempt in range(1, self.MAX_RETRIES_PER_QUESTION + 1):
            try:
                q = self._generate_one(context, previous_stems, angle)
            except Exception as exc:
                logger.warning(f'Generation attempt {attempt} raised: {exc}')
                continue

            if q is None:
                continue

            struct_err = ContentValidator.validate_structure(q)
            if struct_err:
                logger.warning(f'Attempt {attempt} failed structure check: {struct_err}')
                continue

            distractor_warn = ContentValidator.validate_distractors(q)
            if distractor_warn:
                logger.warning(f'Attempt {attempt} distractor quality issue: {distractor_warn}')
                continue

            ContentValidator.check_alignment(q, context)
            return q

        return None

    def _generate_one(
        self, context: str, previous_stems: List[str], angle: str,
    ) -> GeneratedQuestion | None:
        prompt_value = MCQ_SINGLE_PROMPT_BM.invoke({
            'context': context,
            'previous_questions': build_previous_questions_summary(previous_stems),
            'angle': angle,
        })
        response = self._llm.invoke(prompt_value)
        raw = response.content if hasattr(response, 'content') else str(response)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(f'Non-JSON response from Ollama: {exc}; raw={raw[:200]}')
            return None

        try:
            correct_idx_raw = (
                data.get('correct_index')
                if data.get('correct_index') is not None
                else data.get('correctIndex')
                if data.get('correctIndex') is not None
                else data.get('answer')
                if data.get('answer') is not None
                else data.get('correct')
            )
            if correct_idx_raw is None:
                logger.warning(f'No correct-answer key found; data={data}')
                return None

            stem_text = normalize(str(data['stem']).strip())
            return GeneratedQuestion(
                stem=stem_text,
                options=[normalize(str(o).strip()) for o in data['options']],
                correct_index=int(correct_idx_raw),
                explanation=normalize(str(
                    data.get('explanation')
                    or data.get('explain')
                    or data.get('reason')
                    or 'Tiada penjelasan diberikan.'
                ).strip()),
                points=1,
                difficulty=classify_difficulty(stem_text),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f'Malformed question JSON: {exc}; data={data}')
            return None