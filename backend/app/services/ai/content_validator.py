"""
ContentValidator — implements the Section 5 class of the same name.

Checks AI-generated questions against:
  1. Structural rules (4 options, correct_index in range, no empty fields)
  2. KSSM corpus alignment — at least one keyword from the source text
     appears in the question. Soft check; logs warnings, doesn't reject.

Strict validation rejects bad output; soft validation flags it for review.

Phase 1 additions:
  - validate_roman_numeral(): validates Roman Numeral multi-statement questions.
  - Stem length limit raised 250 → 350 to accommodate RN stems that embed
    three statements before the closing question line.
"""
import logging
import re
from typing import Optional

from .base import GeneratedQuestion

_PLACEHOLDER_RE = re.compile(r'^pilihan\s+[abcd]$', re.IGNORECASE)

# Options that start with an option label — LLM including "A." in the text
_OPTION_LABEL_RE = re.compile(r'^[A-D]\.\s+', re.IGNORECASE)

_ESSAY_STARTER_RE = re.compile(
    r'^(?:jelaskan|huraikan|bincangkan|terangkan|nyatakan dan huraikan)\s',
    re.IGNORECASE,
)

_META_STARTER_RE = re.compile(
    r'^(?:jawab(?:apan)?|soalan|nota|catatan|note)\s*[:.]',
    re.IGNORECASE,
)

# Two or more ALLCAPS words (≥4 chars) = gibberish / hallucination signal
_ALLCAPS_GIBBERISH_RE = re.compile(r'(?:\b[A-Z]{4,}\b.*){2}')

# ── Roman Numeral question patterns ───────────────────────────────────────────
# Detects options that are Roman Numeral subset combinations.
# Matches: "I sahaja", "I dan II sahaja", "I dan III sahaja", "II dan III sahaja",
#          "I, II dan III", "I, II, III dan IV", etc.
# meN- verb prefix: mengX, menX, memX, menyX, melX, merX, meX (covers all nasal + other)
_ME_VERB_RE = re.compile(r'^me[a-z]{3,}', re.IGNORECASE)

_RN_OPTION_RE = re.compile(
    r'^(?:[IVX]+(?:,\s*[IVX]+)*(?:\s+dan\s+[IVX]+)?\s+sahaja|[IVX]+(?:,\s*[IVX]+)+\s+dan\s+[IVX]+)$',
    re.IGNORECASE,
)

# Detects Roman numeral statement markers in stem (I / II / III at start of line)
_RN_MARKER_RE = re.compile(r'(?:^|\n)(I{1,3}|IV)\s+\S', re.MULTILINE)

# Valid RN stem closing lines
_RN_CLOSING_RE = re.compile(
    r'yang manakah.*betul\s*\?$',
    re.IGNORECASE,
)


_ALIGNMENT_STOPWORDS = frozenset({
    'yang', 'dan', 'untuk', 'pada', 'dengan', 'dari', 'tidak', 'ini',
    'itu', 'adalah', 'akan', 'telah', 'dalam', 'oleh', 'kepada',
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'are',
    'betul', 'sahaja', 'antara', 'manakah', 'pernyataan',
})


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
            if _PLACEHOLDER_RE.match(opt.strip()):
                return f'option is placeholder label: "{opt}"'
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
        # Indonesian vocabulary check
        from .language_normalizer import find_indonesian_words
        bad = find_indonesian_words(q.stem + ' ' + ' '.join(q.options) + ' ' + (q.explanation or ''))
        if bad:
            return f'Indonesian vocabulary detected: {bad[:3]}'
        return None

    @staticmethod
    def validate_stem_quality(q: GeneratedQuestion) -> Optional[str]:
        """Return None if stem is quiz-quality, or a string describing the failure."""
        stem = (q.stem or '').strip()
        if _META_STARTER_RE.match(stem):
            return f'stem is meta-commentary, not a question: "{stem[:60]}"'
        if _ESSAY_STARTER_RE.match(stem):
            return f'stem is essay-style, not MCQ: "{stem[:60]}"'
        if not stem.endswith('?'):
            return 'stem does not end with question mark'
        # RN questions embed three statements before the closing question line;
        # allow up to 350 chars so they are not unfairly penalised.
        max_len = 350 if _RN_MARKER_RE.search(stem) else 250
        if len(stem) > max_len:
            return f'stem too long ({len(stem)} chars > {max_len})'
        if _ALLCAPS_GIBBERISH_RE.search(stem):
            return f'stem contains ALL-CAPS gibberish (hallucination signal): "{stem[:80]}"'
        return None

    @staticmethod
    def validate_options_clean(q: GeneratedQuestion) -> Optional[str]:
        """Return None if options are free of label-leakage, or a description.

        Detects cases where the LLM prefixes options with 'A.', 'B.' etc.
        despite instructions.  The generator strips these before building the
        GeneratedQuestion, so a non-None result here means the strip failed
        (e.g. mid-string labels).
        Skip this check for Roman Numeral questions — their options legitimately
        start with Roman numerals which share the A-D pattern superficially.
        """
        if ContentValidator._is_roman_numeral_question(q):
            return None
        for i, opt in enumerate(q.options):
            if _OPTION_LABEL_RE.match(opt.strip()):
                return (
                    f'option {i} still has label prefix after cleaning: "{opt[:40]}"'
                )
        return None

    @staticmethod
    def validate_roman_numeral(q: GeneratedQuestion) -> Optional[str]:
        """Validate structure of Roman Numeral multi-statement questions.

        Only runs when the question is detected as RN format.
        Returns None if valid (or if not an RN question), or an error string.
        """
        if not ContentValidator._is_roman_numeral_question(q):
            return None

        stem = (q.stem or '').strip()

        # Stem must contain at least two Roman numeral markers (I, II, III…)
        markers = _RN_MARKER_RE.findall(stem)
        if len(markers) < 2:
            return (
                f'RN question has fewer than 2 Roman numeral markers in stem '
                f'(found {len(markers)}): "{stem[:80]}"'
            )

        # Stem must end with a closing question line
        if not _RN_CLOSING_RE.search(stem):
            return (
                f'RN stem does not end with a "yang manakah ... betul?" closing line: '
                f'"{stem[-60:]}"'
            )

        # All four options must match the RN subset pattern
        for i, opt in enumerate(q.options):
            if not _RN_OPTION_RE.match(opt.strip()):
                return (
                    f'RN option {i} is not a valid Roman Numeral subset: "{opt[:50]}"'
                )

        return None

    @staticmethod
    def _is_roman_numeral_question(q: GeneratedQuestion) -> bool:
        """Return True if this question uses the Roman Numeral multi-statement format.

        Triggers when EITHER:
        - At least 2 of the 4 options match the RN subset pattern
          (e.g. "I dan II sahaja", "I, II dan III"), OR
        - The stem contains at least 2 Roman numeral statement markers
          (e.g. newline-prefixed I / II / III).

        Catching both cases means a malformed RN question (correct stem,
        wrong options) is still validated and rejected rather than silently
        passing through as a regular question.
        """
        stem_has_markers = len(_RN_MARKER_RE.findall(q.stem or '')) >= 2
        if stem_has_markers:
            return True
        if not isinstance(q.options, list):
            return False
        rn_count = sum(1 for o in q.options if _RN_OPTION_RE.match((o or '').strip()))
        return rn_count >= 2

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
        """Check distractor quality — reject low-effort or trivially wrong options.

        Returns None if valid, or a string describing the first failure.
        The caller treats a non-None result as a hard retry trigger.

        Roman Numeral questions are exempt from category-same and near-duplicate
        checks because their distractors are structurally constrained subsets.
        """
        is_rn = ContentValidator._is_roman_numeral_question(q)

        correct = q.options[q.correct_index].strip().lower()
        distractors = [
            q.options[i].strip().lower()
            for i in range(4)
            if i != q.correct_index
        ]

        # All-or-nothing options — useless for MCQ (not applicable to RN)
        if not is_rn:
            trivial_opts = {'semua di atas', 'tiada yang betul', 'tiada jawapan', 'all of the above'}
            for d in distractors:
                if d in trivial_opts:
                    return f'trivial distractor: "{d}"'

        # Near-duplicate distractors (Jaccard > 0.65); RN distractors naturally
        # share Roman numeral tokens so skip this check for them.
        if not is_rn:
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
    def validate_option_length_parity(q: GeneratedQuestion) -> Optional[str]:
        """Reject questions where one option is grossly shorter than another.

        A 3.0:1 character-count ratio (longest / shortest) is the hard cut-off.
        This catches location questions where "Ipoh" sits next to "Amerika Syarikat"
        and gives away the distractor by visual length alone.

        Roman Numeral questions are exempt — their options are structurally
        fixed Roman-numeral subsets with inherently variable token counts.
        """
        if ContentValidator._is_roman_numeral_question(q):
            return None
        if not isinstance(q.options, list) or len(q.options) < 2:
            return None

        lengths = [len(o.strip()) for o in q.options]
        shortest = min(lengths)
        longest = max(lengths)
        if shortest == 0:
            return None  # empty option caught by validate_structure
        ratio = longest / shortest
        if ratio >= 3.0:
            short_opt = q.options[lengths.index(shortest)].strip()
            long_opt = q.options[lengths.index(longest)].strip()
            return (
                f'option length imbalance ({ratio:.1f}:1 ratio): '
                f'"{short_opt}" vs "{long_opt[:40]}"'
            )
        return None

    @staticmethod
    def validate_option_parallelism(q: GeneratedQuestion) -> Optional[str]:
        """Reject action-type questions whose options mix grammatical forms.

        When ≥3 options open with a meN- verb (mengembangkan, meningkatkan…),
        all 4 must — otherwise the odd-one-out is visually telegraphed.
        Questions with fewer than 3 meN- openers are not treated as action-type
        (e.g. date/name/place options are not required to be parallel).

        Roman Numeral questions are exempt — their options are structurally
        fixed Roman-numeral subset strings, not verb phrases.
        """
        if ContentValidator._is_roman_numeral_question(q):
            return None
        if not isinstance(q.options, list) or len(q.options) != 4:
            return None

        me_count = sum(1 for o in q.options if _ME_VERB_RE.match(o.strip()))
        if me_count < 3:
            return None  # not clearly an action-type question

        if me_count < 4:
            non_parallel = [o.strip() for o in q.options if not _ME_VERB_RE.match(o.strip())]
            return (
                f'options not grammatically parallel: {me_count}/4 use meN- verb; '
                f'non-parallel option: "{non_parallel[0][:50]}"'
            )
        return None

    @staticmethod
    def check_alignment(q: GeneratedQuestion, context: str) -> bool:
        """Soft check — does the question reference the source text?

        We extract significant words from the context (length > 4, not
        stop words) and check if any appear in the stem or options. If
        zero overlap, the model probably hallucinated.

        Roman Numeral questions use the full stem (including statements)
        for alignment checking, which gives a better signal since each
        statement should be grounded in the context.
        """
        if not context:
            return True  # nothing to check against

        ctx_words = {
            w.lower().strip('.,;:!?()[]"')
            for w in context.split()
            if len(w) > 4 and w.lower() not in _ALIGNMENT_STOPWORDS
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
