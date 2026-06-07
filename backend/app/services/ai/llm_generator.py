"""
LLM-backed implementation of IQuestionGenerator (currently OpenAI via LangChain).

Generates one question per LLM call so the frontend can stream results as they arrive.
"""
import json
import logging
from typing import Iterator, List, Optional

from langchain_openai import ChatOpenAI

from .base import IQuestionGenerator, GeneratedQuestion
from .content_validator import ContentValidator, _jaccard
from .language_normalizer import normalize
from .llm_config import get_openai_api_key, get_openai_model, get_openai_timeout
from .prompt_templates import (
    MCQ_SINGLE_PROMPT_BM,
    build_previous_questions_summary,
    pick_angle,
    make_shuffled_angle_order,
)
from .quiz_difficulty_classifier import classify_difficulty


logger = logging.getLogger(__name__)


class LlmQuestionGenerator(IQuestionGenerator):

    MAX_RETRIES_PER_QUESTION = 3

    # How many outer generation attempts to allow per requested question.
    # A 10-question quiz gets up to 10 × 4 = 40 attempts before giving up.
    # Each attempt may internally do up to MAX_RETRIES_PER_QUESTION LLM calls,
    # so the absolute worst-case API calls = 40 × 3 = 120 (vs 30 in the old design).
    _BUDGET_MULTIPLIER = 4

    # Jaccard threshold for blocking paraphrases generated in the current run.
    # 0.5 is appropriate because within a single session the LLM should never
    # produce token-overlap this high for a genuinely different question.
    _DEDUP_THRESHOLD = 0.5

    # Looser threshold for cross-attempt historical stems.
    # After multiple attempts on the same chapter, questions about the same
    # topic with different angles (e.g., "kesan 1776" vs "kepentingan 1776")
    # legitimately share many domain tokens.  We only block near-identical
    # wording (>3/4 token overlap) so students can revisit the same facts from
    # fresh angles without the budget exhausting prematurely.
    _CROSS_ATTEMPT_DEDUP_THRESHOLD = 0.75

    def __init__(self):
        self._llm = ChatOpenAI(
            api_key=get_openai_api_key(),
            model=get_openai_model(),
            temperature=0.75,
            max_tokens=512,
            timeout=get_openai_timeout(),
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    def generate_stream(
        self,
        context: str,
        num_questions: int,
        language: str = 'bm',
        seen_stems: Optional[List[str]] = None,
        difficulty: str = 'medium',
    ) -> Iterator[GeneratedQuestion]:
        """Yield questions one-by-one until num_questions valid questions exist.

        Uses a budget-based outer loop so validation failures and dedup rejects
        do NOT permanently consume a question slot.  The loop keeps trying new
        angle/question combinations until the target is reached or the budget
        (num_questions × _BUDGET_MULTIPLIER outer attempts) is exhausted.

        Args:
            context:       KSSM source text (already truncated by caller).
            num_questions: How many valid MCQs to produce.
            language:      Only 'bm' is supported.
            seen_stems:    Stems from *previous* attempts on the same quiz.
                           Seeded into the dedup list for cross-attempt protection.
        """
        if language != 'bm':
            logger.warning(f"Language '{language}' not yet supported, falling back to BM.")

        max_context_chars = 8000
        ctx = context[:max_context_chars] if len(context) > max_context_chars else context

        # Separate tracking: historical stems use a looser cross-attempt threshold
        # so the same topic can be revisited from a different angle across attempts.
        # Current-run stems use the strict within-run threshold to catch paraphrases.
        historical: List[str] = list(seen_stems or [])
        current_run: List[str] = []  # stems produced in this generation session

        # Expand the budget when there are many historical stems to dodge.
        # More history → more outer attempts needed before a fresh question clears
        # all dedup checks, so we give the loop proportionally more room.
        history_count = len(historical)
        budget_multiplier = self._BUDGET_MULTIPLIER + (2 if history_count > 15 else 0)
        budget = num_questions * budget_multiplier
        angle_order = make_shuffled_angle_order(budget, difficulty=difficulty)

        produced_count = 0   # successfully validated & yielded questions this run
        outer_attempt = 0    # total outer loop iterations consumed

        while produced_count < num_questions and outer_attempt < budget:
            angle_name, angle_instruction, _ = pick_angle(outer_attempt, angle_order)
            outer_attempt += 1

            all_previous = historical + current_run
            q = self._generate_one_with_retries(
                ctx,
                all_previous,
                angle_name,
                angle_instruction,
            )
            if q is None:
                logger.debug(
                    f'Outer attempt {outer_attempt}/{budget}: question failed all retries '
                    f'(have {produced_count}/{num_questions}).'
                )
                continue

            # Two-tier dedup:
            #   historical stems → _CROSS_ATTEMPT_DEDUP_THRESHOLD (lenient)
            #   current-run stems → _DEDUP_THRESHOLD (strict)
            if self._is_duplicate(q.stem, historical, self._CROSS_ATTEMPT_DEDUP_THRESHOLD):
                logger.debug(
                    f'Outer attempt {outer_attempt}/{budget}: cross-attempt duplicate, skipping.'
                )
                continue
            if self._is_duplicate(q.stem, current_run, self._DEDUP_THRESHOLD):
                logger.debug(
                    f'Outer attempt {outer_attempt}/{budget}: within-run duplicate, skipping.'
                )
                continue

            current_run.append(q.stem)
            produced_count += 1
            yield q

        if produced_count < num_questions:
            logger.warning(
                f'generate_stream budget exhausted: produced {produced_count}/{num_questions} '
                f'after {outer_attempt} outer attempts '
                f'(budget={budget}, seen_stems={len(seen_stems or [])}).'
            )

    def _is_duplicate(
        self,
        stem: str,
        previous_stems: List[str],
        threshold: float = 0.5,
    ) -> bool:
        """Return True if stem is too similar to any stem in previous_stems.

        Args:
            stem:            Candidate question stem.
            previous_stems:  Stems to compare against.
            threshold:       Jaccard score at-or-above which the candidate is
                             considered a duplicate.  Use _DEDUP_THRESHOLD for
                             within-run checks and _CROSS_ATTEMPT_DEDUP_THRESHOLD
                             for historical stems from prior attempts.
        """
        for prev in previous_stems:
            if _jaccard(stem.lower(), prev.lower()) >= threshold:
                return True
        return False

    # ── internals ─────────────────────────────────────────────────────────────

    def _generate_one_with_retries(
        self,
        context: str,
        previous_stems: List[str],
        angle_name: str,
        angle_instruction: str,
    ) -> Optional[GeneratedQuestion]:
        for attempt in range(1, self.MAX_RETRIES_PER_QUESTION + 1):
            try:
                q = self._generate_one(context, previous_stems, angle_name, angle_instruction)
            except Exception as exc:
                logger.warning(f'Generation attempt {attempt} raised: {exc}')
                continue

            if q is None:
                continue

            struct_err = ContentValidator.validate_structure(q)
            if struct_err:
                logger.warning(f'Attempt {attempt} failed structure check: {struct_err}')
                continue

            stem_err = ContentValidator.validate_stem_quality(q)
            if stem_err:
                logger.warning(f'Attempt {attempt} failed stem quality check: {stem_err}')
                continue

            opts_err = ContentValidator.validate_options_clean(q)
            if opts_err:
                logger.warning(f'Attempt {attempt} failed options-clean check: {opts_err}')
                continue

            rn_err = ContentValidator.validate_roman_numeral(q)
            if rn_err:
                logger.warning(f'Attempt {attempt} failed Roman Numeral check: {rn_err}')
                continue

            distractor_warn = ContentValidator.validate_distractors(q)
            if distractor_warn:
                logger.warning(f'Attempt {attempt} distractor quality issue: {distractor_warn}')
                continue

            parity_err = ContentValidator.validate_option_length_parity(q)
            if parity_err:
                logger.warning(f'Attempt {attempt} failed option length parity: {parity_err}')
                continue

            parallelism_err = ContentValidator.validate_option_parallelism(q)
            if parallelism_err:
                logger.warning(f'Attempt {attempt} failed option parallelism: {parallelism_err}')
                continue

            if not ContentValidator.check_alignment(q, context):
                logger.warning(
                    f'Attempt {attempt} failed alignment check — possible hallucination, retrying'
                )
                continue

            return q

        return None

    def _generate_one(
        self,
        context: str,
        previous_stems: List[str],
        angle_name: str,
        angle_instruction: str,
    ) -> Optional[GeneratedQuestion]:
        prompt_value = MCQ_SINGLE_PROMPT_BM.invoke({
            'context': context,
            'previous_questions': build_previous_questions_summary(previous_stems),
            'angle_name': angle_name,
            'angle_instruction': angle_instruction,
        })
        response = self._llm.invoke(prompt_value)
        raw = response.content if hasattr(response, 'content') else str(response)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(f'Non-JSON response from LLM: {exc}; raw={raw[:200]}')
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

            # Strip option-label leakage: LLM sometimes prefixes options with
            # "A. ", "B. " etc. despite instructions.  Remove them here so the
            # validator sees clean text rather than failing on content mismatch.
            import re as _re
            _label_re = _re.compile(r'^[A-D]\.\s+', _re.IGNORECASE)
            raw_opts = [normalize(str(o).strip()) for o in data['options']]
            cleaned_opts = [_label_re.sub('', o) for o in raw_opts]

            return GeneratedQuestion(
                stem=stem_text,
                options=cleaned_opts,
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
