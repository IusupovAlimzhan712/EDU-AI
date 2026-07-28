"""
BM question-type classifier for the AI tutor pipeline.

Returns one of:
  'factual'    — apakah, siapakah, senaraikan, nyatakan, bilakah
  'comparison' — bezakan, bandingkan, apakah perbezaan / persamaan
  'kbat'       — mengapa, bagaimana, huraikan, bincangkan (default)

Also exposes is_social_message() which detects greetings, thanks, and
study-support phrases that should bypass KB retrieval entirely.

Used to:
  1. Inject mode-specific prompt instructions (extractive vs reasoning)
  2. Set the dynamic num_predict (token) limit for Ollama
  3. Short-circuit social messages before retrieval
"""
import re

# ── Pattern lists ─────────────────────────────────────────────────────────
# Comparison must be checked BEFORE factual because "apakah perbezaan"
# starts with "apakah" (a factual marker) but is actually a comparison.

_COMPARISON = [
    r'\bbez[ae]kan\b',
    r'\bbandingkan\b',
    r'\bperbezaan\b',
    r'\bpersamaan\b',
    r'\bberbeza\b',
    r'\bsama ada\b',
    r'\bvsb?\b',        # shorthand "vs"
]

_FACTUAL = [
    r'^apakah\b',
    r'^siapakah\b',
    r'^bilakah\b',
    r'^di manakah\b',
    r'^berapa\b',
    r'^nyatakan\b',
    r'^senaraikan\b',
    r'^namakan\b',
    r'^apakah ciri',
    r'^apakah maksud',
    r'^apakah yang dimaksudkan',
    r'\bsenaraikan\b',
    r'\bnyatakan\b',
    r'\bnamakan\b',
    r'\bapakah ciri',
    r'\bapakah faktor',
    r'\bapakah tujuan',
    r'\bapakah kesan\b',
]

_KBAT = [
    r'^mengapa\b',
    r'^bagaimana\b',
    r'^huraikan\b',
    r'^jelaskan\b',
    r'^bincangkan\b',
    r'^nilaikan\b',
    r'^buktikan\b',
    r'^rumuskan\b',
    r'^ramalkan\b',
    r'^analisis',
    r'^terangkan\b',
    r'^beri pendapat',
    r'^berikan hujah',
]

_RE_COMPARISON = [re.compile(p, re.IGNORECASE) for p in _COMPARISON]
_RE_FACTUAL    = [re.compile(p, re.IGNORECASE) for p in _FACTUAL]
_RE_KBAT       = [re.compile(p, re.IGNORECASE) for p in _KBAT]

# ── Token limits per mode (Ollama num_predict cap) ─────────────────────────
# These are CAPS, not targets — the model stops at EOS regardless.
# Short caps prevent over-explanation for factual questions.
MODE_TOKENS: dict[str, int] = {
    'factual':    400,   # list + 1-sentence explanation per item
    'comparison': 500,   # side-by-side comparison with explanations
    'kbat':       600,   # reasoning/explanation with evidence
}


# ── Social / casual message detection ────────────────────────────────────────
# These patterns identify messages that need a warm conversational reply,
# NOT knowledge-base retrieval. Checked BEFORE the academic pipeline.

_RE_SOCIAL_GREETING = re.compile(
    r'^(?:hi|hello|hey|helo|hai|yo)\b'
    r'|^(?:selamat\s+(?:pagi|tengahari|tengah\s*hari|petang|malam|sejahtera))\b'
    r'|^(?:assalamualaikum|a(?:s+)alamu?(?:alaikum)?|waalaikumsalam|salam)\b'
    r'|^good\s+(?:morning|afternoon|evening|night)\b',
    re.IGNORECASE,
)

_RE_SOCIAL_THANKS = re.compile(
    r'^(?:terima\s*kasih|thanks?|thank\s+you|tq|thx|syukran|jazakallah)\b',
    re.IGNORECASE,
)

_RE_SOCIAL_FAREWELL = re.compile(
    r'^(?:bye|goodbye|tata|jumpa\s+lagi|sampai\s+jumpa|selamat\s+tinggal|good\s*night)\b',
    re.IGNORECASE,
)

_RE_SOCIAL_STUDY_SUPPORT = re.compile(
    r'\b(?:penat|tired|exhausted|blur|confused|keliru|sedih|stress|risau|nervous|bosan)\b'
    r'|\b(?:susah(?:nya|lah?|betul|sangat|gila)?|hard|difficult)\b'
    r'|^(?:exam|peperiksaan|test|ujian)\s+(?:esok|besok|tomorrow|minggu\s*depan|lusa)\b'
    r'|^(?:ada\s+exam|nak\s+(?:belajar|ulang\s*kaji|study))\b'
    r'|^(?:boleh\s+(?:tak|kah)?\s*(?:tolong|bantu|ajar))\b'
    r'|^(?:tolong\s+(?:bantu|ajar)\s+(?:saya|aku))\b'
    r'|^(?:can\s+you\s+help|help\s+me|i\s+(?:need|want)\s+help)\b',
    re.IGNORECASE,
)

_RE_SOCIAL_AFFIRMATION = re.compile(
    r'^(?:ok|okay|alright|baik|faham|paham|got\s+it|i\s+see|noted|roger|boleh|fine)'
    r'(?:\s+(?:ok|okay|faham|paham|baik|la|je|juga|sudah|lah))?\s*[!.]*$',
    re.IGNORECASE,
)

# If ANY of these historical keywords appear, the message is academic not social.
_RE_HISTORY_KEYWORD = re.compile(
    r'\b(?:'
    r'sejarah|bab|tingkatan|form\s*[45]'
    r'|sultan|raja|kolonial|british|jepun|portugis|belanda|inggeris|dutch'
    r'|kemerdekaan|penjajah|perang|dasar|perlembagaan|parlimen|merdeka'
    r'|melayu|melaka|perak|selangor|kesultanan|tokoh|pahlawan|pejuang'
    r'|kssm|spm|spr|malayan|federation|persekutuan'
    r'|1[0-9]{3}'
    r')\b',
    re.IGNORECASE,
)

_SOCIAL_CHECKS = (
    _RE_SOCIAL_GREETING,
    _RE_SOCIAL_THANKS,
    _RE_SOCIAL_FAREWELL,
    _RE_SOCIAL_STUDY_SUPPORT,
    _RE_SOCIAL_AFFIRMATION,
)


def is_social_message(question: str) -> bool:
    """Return True if the message is casual/social and should bypass KB retrieval.

    Study-support / emotional messages are classified as social even when they
    mention subject names like "Sejarah" ("Susahnya Sejarah ni" is emotional
    support, not an academic query).  All other social patterns (greetings,
    thanks, farewells) are blocked by history keywords to prevent academic
    questions from accidentally matching.
    """
    q = question.strip()
    # Study-support patterns bypass the history-keyword guard — a student saying
    # "Susahnya Sejarah ni, rasa nak give up" is venting, not asking a factual Q.
    if _RE_SOCIAL_STUDY_SUPPORT.search(q):
        return True
    if _RE_HISTORY_KEYWORD.search(q):
        return False
    return any(pattern.search(q) for pattern in _SOCIAL_CHECKS)


def classify_question(question: str) -> str:
    """Classify a BM question into 'factual' | 'comparison' | 'kbat'.

    Comparison takes priority — "apakah perbezaan" starts with "apakah"
    but is a comparison, not a simple factual recall.
    Defaults to 'kbat' for open-ended or unrecognized patterns.
    """
    q = question.strip()
    for pattern in _RE_COMPARISON:
        if pattern.search(q):
            return 'comparison'
    for pattern in _RE_FACTUAL:
        if pattern.search(q):
            return 'factual'
    for pattern in _RE_KBAT:
        if pattern.search(q):
            return 'kbat'
    return 'kbat'
