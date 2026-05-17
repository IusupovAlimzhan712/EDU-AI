"""
Validators for tutor chat responses.

Check order in validate():
  1. Empty / too short
  2. Broken Unicode (encoding failure)
  3. Too long
  4. Non-Latin script (Arabic, Chinese, Hebrew, etc.)
  5. Language — not predominantly English
  6. Language — has BM markers
  7. Indonesian vocabulary leaked through normalizer
  8. Date contradiction (answer introduces years not in context)
  9. Semantic grounding — keyword overlap too low (heavy hallucination)
 10. Legitimate refusals / uncertainty phrases → always ok
"""
import logging
import re
from typing import Optional, Tuple

from .content_validator import ContentValidator
from .language_normalizer import find_indonesian_words, has_broken_unicode


logger = logging.getLogger(__name__)


# ── BM / English word sets ─────────────────────────────────────────────────

BM_MARKER_WORDS = {
    'yang', 'dan', 'untuk', 'pada', 'dengan', 'dari', 'tidak', 'ini', 'itu',
    'adalah', 'akan', 'telah', 'dalam', 'oleh', 'kepada', 'mereka', 'kita',
    'kami', 'anda', 'saya', 'beliau', 'apa', 'apabila', 'mengapa', 'bagaimana',
    'kerana', 'tetapi', 'maka', 'juga', 'boleh', 'ialah', 'iaitu', 'sahaja',
    'hanya', 'sangat', 'lebih', 'paling', 'banyak', 'sedikit', 'merupakan',
    'menjadi', 'membawa', 'memberi', 'mendapat', 'tahun', 'atau', 'serta',
    'bukan', 'jadi', 'maaf', 'sila', 'berdasarkan', 'halaman', 'maklumat',
    'dinyatakan', 'terdapat', 'tersebut', 'bahawa',
    # Formal/academic register markers common in historical BM texts
    'sebagai', 'manakala', 'turut', 'antaranya', 'namun', 'walau',
    'setelah', 'selepas', 'sebelum', 'apabila', 'semasa', 'ketika',
    'baginda', 'terdiri', 'meliputi', 'melibatkan', 'mengandungi',
}

ENGLISH_MARKER_WORDS = {
    'the', 'is', 'are', 'was', 'were', 'has', 'have', 'had', 'will',
    'would', 'could', 'should', 'i', 'you', 'he', 'she', 'we', 'they',
    'my', 'your', 'his', 'her', 'our', 'their', 'this', 'that', 'these',
    'those', 'with', 'for', 'from', 'about', 'into', 'over', 'under',
    'between', 'because', 'when', 'where', 'what', 'who', 'why', 'how',
    'can', 'do', 'does', 'did', 'not', 'no', 'yes', 'and', 'but', 'or',
    'as', 'an', 'a', 'of', 'in', 'on', 'at', 'to', 'by',
}

# Stopwords for keyword-overlap analysis (both BM and EN)
_GROUNDING_STOPWORDS = {
    'yang', 'dan', 'untuk', 'pada', 'dengan', 'dari', 'tidak', 'ini', 'itu',
    'adalah', 'akan', 'telah', 'dalam', 'oleh', 'kepada', 'mereka', 'kita',
    'kami', 'anda', 'saya', 'beliau', 'apa', 'apabila', 'kerana', 'tetapi',
    'maka', 'juga', 'boleh', 'ialah', 'iaitu', 'sahaja', 'hanya', 'sangat',
    'lebih', 'paling', 'banyak', 'sedikit', 'menjadi', 'jadi', 'bukan',
    'atau', 'serta', 'semua', 'setiap', 'antara', 'seperti', 'sebelum',
    'selepas', 'semasa', 'tersebut', 'berdasarkan', 'halaman', 'maklumat',
    'bahawa', 'dinyatakan', 'terdapat', 'merupakan',
    # EN
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'are', 'was',
    'were', 'been', 'being', 'into', 'onto', 'upon',
}

# Refusal / uncertainty phrases → always 'ok'
_REFUSAL_PHRASES = [
    'saya hanya boleh membantu',
    'sila tanya soalan tentang',
    'maklumat ini tidak terdapat',
    'maaf, saya tidak boleh',
    'saya hanya boleh menjawab',
    'tidak dinyatakan secara jelas',
    'berdasarkan halaman ini',
    'berdasarkan bahan rujukan',
    'berdasarkan teks rujukan',
]

# Historical years range (4-digit) — only validate years 1000–2000
_YEAR_RE = re.compile(r'\b1[0-9]{3}\b')


class TutorValidator:

    MIN_LENGTH_CHARS = 15
    MAX_LENGTH_CHARS = 6000

    # 0.30 allows proper nouns, borrowed terms, dates in Malay historical text
    MAX_ENGLISH_WORD_RATIO = 0.30
    MIN_BM_MARKER_COUNT = 2

    # Semantic grounding — if < this fraction of content words is grounded → warn
    # Set low (0.20) to avoid false positives with BM morphological variation and synonyms
    MIN_GROUNDING_RATIO = 0.20
    # Only apply grounding check if answer has at least this many content words
    MIN_GROUNDING_WORDS = 12

    @staticmethod
    def validate(
        response: str,
        page_context: str,
    ) -> Tuple[str, Optional[str]]:
        """Return ('ok' | 'warned', warning_message_or_None).

        Assumes *response* has already been run through language_normalizer.normalize().
        """
        if not response or not response.strip():
            return ('warned', 'AI mengembalikan jawapan kosong.')

        text = response.strip()

        # 1. Too short
        if len(text) < TutorValidator.MIN_LENGTH_CHARS:
            return ('warned', 'Jawapan AI terlalu pendek.')

        # 2. Broken Unicode
        if has_broken_unicode(text):
            return ('warned', 'Jawapan mengandungi aksara rosak (ralat pengekodan).')

        # 3. Too long
        if len(text) > TutorValidator.MAX_LENGTH_CHARS:
            return ('warned', 'Jawapan AI terlalu panjang.')

        # 4. Non-Latin script
        if not ContentValidator.is_predominantly_latin(text):
            return ('warned', 'Jawapan mengandungi aksara bukan-Latin.')

        # 5 & 6. Language detection — strip markdown before tokenizing
        words = TutorValidator._tokenize(text)
        if not words:
            return ('warned', 'Jawapan tidak boleh diproses.')

        english_count = sum(1 for w in words if w in ENGLISH_MARKER_WORDS)
        bm_count      = sum(1 for w in words if w in BM_MARKER_WORDS)
        english_ratio = english_count / len(words)

        if english_ratio > TutorValidator.MAX_ENGLISH_WORD_RATIO:
            return (
                'warned',
                f'Jawapan kelihatan dalam Bahasa Inggeris '
                f'({int(english_ratio * 100)}% perkataan English).',
            )

        if bm_count < TutorValidator.MIN_BM_MARKER_COUNT:
            return ('warned', 'Jawapan tidak kelihatan dalam Bahasa Malaysia.')

        # 7. Indonesian vocabulary safety-net
        bad_words = find_indonesian_words(text)
        if bad_words:
            sample = ', '.join(bad_words[:3])
            logger.warning('Indonesian words leaked past normalizer: %s', bad_words)
            return (
                'warned',
                f'Jawapan mengandungi perkataan bahasa Indonesia: {sample}.',
            )

        # 8. Date contradiction — flag years in answer not found in context
        date_warn = TutorValidator._check_date_grounding(text, page_context)
        if date_warn:
            return ('warned', date_warn)

        # 9. Semantic grounding — keyword overlap too low
        grounding_warn = TutorValidator._check_semantic_grounding(text, page_context)
        if grounding_warn:
            return ('warned', grounding_warn)

        # 10. Legitimate refusal / uncertainty → always ok
        lower_text = text.lower()
        if any(p in lower_text for p in _REFUSAL_PHRASES):
            return ('ok', None)

        return ('ok', None)

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list:
        """Strip markdown syntax + punctuation, lowercase, split."""
        cleaned = []
        for w in text.split():
            t = w.lower().strip('*#_`~.,;:!?()[]"\'->')
            if t and len(t) > 1:
                cleaned.append(t)
        return cleaned

    @staticmethod
    def _check_date_grounding(answer: str, context: str) -> Optional[str]:
        """Warn if answer contains 4-digit historical years absent from context.

        Only checks years in 1000–1999 range (clearly historical).
        Skips check if context has no years (context may be non-historical text).
        """
        ctx_years = set(_YEAR_RE.findall(context))
        if not ctx_years:
            return None  # context has no years — can't meaningfully compare

        ans_years = set(_YEAR_RE.findall(answer))
        unsupported = ans_years - ctx_years
        if unsupported:
            years_str = ', '.join(sorted(unsupported))
            logger.warning('Answer introduced unsupported year(s): %s', years_str)
            return (
                f'Jawapan mengandungi tahun ({years_str}) yang tidak disebut '
                f'dalam teks rujukan — mungkin tidak tepat.'
            )
        return None

    @staticmethod
    def _check_semantic_grounding(answer: str, context: str) -> Optional[str]:
        """Warn if answer content words have very low overlap with context.

        Uses word-set + 5-char prefix matching for BM morphological variation.
        Only fires for sufficiently long answers (>= MIN_GROUNDING_WORDS content words).
        """
        ans_words = TutorValidator._extract_content_words(answer)
        if len(ans_words) < TutorValidator.MIN_GROUNDING_WORDS:
            return None  # too short to check reliably

        # Build lookup sets from context: exact words + 5-char prefixes
        ctx_words = TutorValidator._extract_content_words(context)
        ctx_prefixes = {w[:5] for w in ctx_words if len(w) >= 5}

        grounded = sum(
            1 for w in ans_words
            if w in ctx_words or (len(w) >= 5 and w[:5] in ctx_prefixes)
        )
        ratio = grounded / len(ans_words)

        if ratio < TutorValidator.MIN_GROUNDING_RATIO:
            logger.warning(
                'Semantic grounding low: %.0f%% of content words found in context '
                '(threshold %.0f%%). Grounded=%d / Total=%d',
                ratio * 100, TutorValidator.MIN_GROUNDING_RATIO * 100,
                grounded, len(ans_words),
            )
            return 'Jawapan mungkin mengandungi maklumat tidak disokong oleh teks rujukan.'
        return None

    @staticmethod
    def _extract_content_words(text: str) -> set:
        """Extract significant lowercase words (length ≥ 4, not stopwords)."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        return {w for w in words if w not in _GROUNDING_STOPWORDS}
