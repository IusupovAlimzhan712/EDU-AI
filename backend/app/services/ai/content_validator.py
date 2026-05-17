"""
ContentValidator — implements the Section 5 class of the same name.

Checks AI-generated questions against:
  1. Structural rules (4 options, correct_index in range, no empty fields)
  2. KSSM corpus alignment — at least one keyword from the source text
     appears in the question. Soft check; logs warnings, doesn't reject.

Strict validation rejects bad output; soft validation flags it for review.
"""
import logging
from typing import Optional

from .base import GeneratedQuestion


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


logger = logging.getLogger(__name__)


class ContentValidator:

    @staticmethod
    def validate_structure(q: GeneratedQuestion) -> Optional[str]:
        """Return None if valid, or a string describing the first failure."""
        if not q.stem or not q.stem.strip():
            return 'empty stem'
        if not isinstance(q.options, list) or len(q.options) != 4:
            return f'expected 4 options, got {len(q.options) if isinstance(q.options, list) else "non-list"}'
        for i, opt in enumerate(q.options):
            if not isinstance(opt, str) or not opt.strip():
                return f'option {i} is empty or non-string'
        if not isinstance(q.correct_index, int) or not (0 <= q.correct_index <= 3):
            return f'correct_index out of range: {q.correct_index}'
        # Duplicate options usually = model error
        if len(set(o.strip().lower() for o in q.options)) < 4:
            return 'duplicate options'
        if not q.explanation or not q.explanation.strip():
            return 'empty explanation'
        # Language drift check — reject questions that slipped into Hebrew/Arabic/etc.
        full_text = q.stem + ' ' + ' '.join(q.options) + ' ' + (q.explanation or '')
        if not ContentValidator.is_predominantly_latin(full_text):
            return 'contains non-Latin characters (language drift)'
        return None
    
    @staticmethod
    def is_predominantly_latin(text: str) -> bool:
        """Return False if text contains too many non-Latin characters.

        Catches language drift: Hebrew, Arabic, Chinese, Tamil, etc.
        Allows a small margin (e.g. typos, accented BM letters).
        """
        if not text:
            return True
        # Count characters in the Latin block (basic + extended)
        latin_count = 0
        non_latin_alpha = 0
        for ch in text:
            if ch.isalpha():
                code = ord(ch)
                # Basic Latin (A-Z, a-z) + Latin-1 Supplement + Latin Extended
                if code < 0x024F:
                    latin_count += 1
                else:
                    non_latin_alpha += 1
        total_alpha = latin_count + non_latin_alpha
        if total_alpha == 0:
            return True
        # Reject if more than 5% of alphabetic chars are non-Latin
        return (non_latin_alpha / total_alpha) < 0.05

    @staticmethod
    def validate_distractors(q: GeneratedQuestion) -> Optional[str]:
        """Check distractor quality — flag low-effort or trivially wrong options.

        Returns a warning string (not None) if a problem is detected; the
        caller logs it but still yields the question (soft check).
        """
        correct = q.options[q.correct_index].strip().lower()
        distractors = [
            q.options[i].strip().lower()
            for i in range(4)
            if i != q.correct_index
        ]

        # All-or-nothing options — useless for MCQ
        trivial_opts = {'semua di atas', 'tiada yang betul', 'tiada jawapan', 'all of the above'}
        for d in distractors:
            if d in trivial_opts:
                return f'trivial distractor: "{d}"'

        # Near-duplicate distractors (Jaccard > 0.65)
        for i in range(len(distractors)):
            for j in range(i + 1, len(distractors)):
                if _jaccard(distractors[i], distractors[j]) > 0.65:
                    return f'near-duplicate distractors: "{distractors[i]}" vs "{distractors[j]}"'

        # Distractor same as correct answer
        for d in distractors:
            if d == correct:
                return f'distractor matches correct answer: "{d}"'

        return None

    @staticmethod
    def check_alignment(q: GeneratedQuestion, context: str) -> bool:
        """Soft check — does the question reference the source text?

        We extract significant words from the context (length > 4, not
        stop words) and check if any appear in the stem or options. If
        zero overlap, the model probably hallucinated.
        """
        if not context:
            return True  # nothing to check against

        # Simple BM/EN stopword list. Not exhaustive, but enough.
        STOPWORDS = {
            'yang', 'dan', 'untuk', 'pada', 'dengan', 'dari', 'tidak', 'ini',
            'itu', 'adalah', 'akan', 'telah', 'dalam', 'oleh', 'kepada',
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'are',
        }

        ctx_words = {
            w.lower().strip('.,;:!?()[]"')
            for w in context.split()
            if len(w) > 4 and w.lower() not in STOPWORDS
        }
        if not ctx_words:
            return True

        check_text = (q.stem + ' ' + ' '.join(q.options)).lower()
        overlap = any(w in check_text for w in ctx_words)
        if not overlap:
            logger.warning(
                'AI question has zero keyword overlap with source — possible hallucination. '
                f'Stem: {q.stem[:80]}'
            )
        return overlap