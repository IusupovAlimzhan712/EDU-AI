"""
BM question-type classifier for the AI tutor pipeline.

Returns one of:
  'factual'    — apakah, siapakah, senaraikan, nyatakan, bilakah
  'comparison' — bezakan, bandingkan, apakah perbezaan / persamaan
  'kbat'       — mengapa, bagaimana, huraikan, bincangkan (default)

Used to:
  1. Inject mode-specific prompt instructions (extractive vs reasoning)
  2. Set the dynamic num_predict (token) limit for Ollama
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
    'factual':    150,   # 1-3 sentences or a short list
    'comparison': 280,   # side-by-side comparison, up to 5 points
    'kbat':       400,   # reasoning/explanation with evidence
}


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
