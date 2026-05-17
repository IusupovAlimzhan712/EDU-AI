"""
Language normalization for AI tutor responses.

Two responsibilities:
  1. Indonesian → Bahasa Malaysia vocabulary replacement
  2. Unicode sanitization (broken chars, null bytes, control characters)

Applied to the complete response buffer BEFORE validation and final yield,
so streamed tokens go out raw but the final persisted/rendered text is clean.
"""
import re
import unicodedata


# Ordered list of (compiled_regex, replacement) pairs.
# Longer / more specific patterns must come first.
_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # ── Forbidden Indonesian vocabulary → BM equivalents ──────────────
    (re.compile(r'\bkontribusinya\b', re.IGNORECASE), 'sumbangannya'),
    (re.compile(r'\bkontribusi\b',    re.IGNORECASE), 'sumbangan'),
    (re.compile(r'\bpangeran\b',      re.IGNORECASE), 'putera'),
    (re.compile(r'\bTiongkok\b'),                      'China'),
    (re.compile(r'\btiongkok\b'),                      'china'),

    # bahwa / bahwa → bahawa (Indonesian spelling)
    (re.compile(r'\bbahwa\b',         re.IGNORECASE), 'bahawa'),

    # karena → kerana (Indonesian spelling)
    (re.compile(r'\bkarena\b',        re.IGNORECASE), 'kerana'),

    # dikarenakan → kerana / disebabkan
    (re.compile(r'\bdisebabkan karena\b', re.IGNORECASE), 'disebabkan oleh'),
    (re.compile(r'\bdikarenakan\b',   re.IGNORECASE), 'kerana'),

    # memiliki → mempunyai (Indonesian verb form)
    (re.compile(r'\bmemiliki\b',      re.IGNORECASE), 'mempunyai'),

    # menyebutkan → menyatakan (Indonesian formal verb)
    (re.compile(r'\bmenyebutkan\b',   re.IGNORECASE), 'menyatakan'),

    # mengatakan → menyatakan (more formal, textbook appropriate)
    # (kept optional — "mengatakan" is also valid BM in spoken register)

    # oknum → individu
    (re.compile(r'\boknum\b',         re.IGNORECASE), 'individu'),

    # Informal Indonesian fillers (should never appear in formal answers)
    (re.compile(r'\bbanget\b',        re.IGNORECASE), 'sangat'),
    (re.compile(r'\bgimana\b',        re.IGNORECASE), 'bagaimana'),
    (re.compile(r'\bnggak\b',         re.IGNORECASE), 'tidak'),
    (re.compile(r'\bngga\b',          re.IGNORECASE), 'tidak'),
    (re.compile(r'\bgak\b',           re.IGNORECASE), 'tidak'),
    (re.compile(r'\budah\b',          re.IGNORECASE), 'sudah'),
    (re.compile(r'\baja\b',           re.IGNORECASE), 'sahaja'),
    (re.compile(r'\bemang\b',         re.IGNORECASE), 'memang'),

    # Overexplaining filler phrases the AI uses in Indonesian style
    (re.compile(r'\bhal ini menunjukkan bahwa\b', re.IGNORECASE), 'ini menunjukkan bahawa'),
    (re.compile(r'\bhal tersebut\b',  re.IGNORECASE), 'perkara tersebut'),
]

# Words that signal potential Indonesian usage — used by the validator
# as a safety-net AFTER normalization (catches patterns the regex missed).
INDONESIAN_MARKERS: frozenset[str] = frozenset({
    'kontribusi', 'pangeran', 'tiongkok', 'dikarenakan', 'oknum',
    'banget', 'gimana', 'gue', 'gua', 'emang', 'udah', 'aja',
    'nggak', 'ngga', 'gak', 'kayak', 'tuh', 'nih', 'sih', 'doang',
    'bahwa', 'karena', 'memiliki', 'menyebutkan',
})

# U+FFFD = Unicode replacement character (signals encoding failure)
_REPLACEMENT_CHAR = '�'

# Control characters to strip (keep \n=0x0A, \t=0x09, \r=0x0D)
_CTRL_CHAR_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')


def normalize(text: str) -> str:
    """Return a clean, BM-normalized version of *text*.

    Steps (in order):
      1. Unicode NFC normalization — fixes decomposed / composed char issues
      2. Strip null bytes + control characters (keep newline, tab, CR)
      3. Remove U+FFFD replacement characters (broken encoding)
      4. Apply Indonesian → BM vocabulary replacements
    """
    if not text:
        return text

    # 1. NFC normalization
    text = unicodedata.normalize('NFC', text)

    # 2. Control chars
    text = _CTRL_CHAR_RE.sub('', text)

    # 3. Broken-encoding markers
    text = text.replace(_REPLACEMENT_CHAR, '')

    # 4. Vocabulary replacements
    for pattern, replacement in _REPLACEMENTS:
        text = pattern.sub(replacement, text)

    return text


def find_indonesian_words(text: str) -> list[str]:
    """Return any Indonesian marker words still present in *text* (after normalize).

    Used by TutorValidator as a belt-and-suspenders check.
    """
    words = {w for w in re.findall(r'\b[a-z]+\b', text.lower())}
    return sorted(words & INDONESIAN_MARKERS)


def has_broken_unicode(text: str) -> bool:
    """Return True if *text* contains U+FFFD replacement characters."""
    return _REPLACEMENT_CHAR in text
