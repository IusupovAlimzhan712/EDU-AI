"""
Difficulty classifier for generated MCQ questions.

Classifies a generated question as 'mudah' | 'sederhana' | 'sukar' using
simple heuristics — no LLM call needed.

Signals:
  mudah   — factual recall: who/when/where answered directly in context
  sederhana — applied understanding: why/how/what effect (requires inference)
  sukar   — synthesis/KBAT: compare, evaluate, analyse, justify
"""
import re
from typing import Literal

DifficultyLevel = Literal['mudah', 'sederhana', 'sukar']

_RE_MUDAH = re.compile(
    r'\b(?:'
    r'siapa(?:kah)?'
    r'|bila(?:kah)?'
    r'|tahun\s+berapa'
    r'|di\s+mana(?:kah)?'
    r'|apakah\s+nama'
    r'|berapa\b'
    r')\b',
    re.IGNORECASE,
)

_RE_SUKAR = re.compile(
    r'\b(?:'
    r'bandingkan'
    r'|bezakan'
    r'|perbezaan\s+antara'
    r'|persamaan\s+antara'
    r'|nilaikan'
    r'|huraikan\s+kepentingan'
    r'|jelaskan\s+kesan'
    r'|analisis(?:kan)?'
    r'|justifikasi(?:kan)?'
    r'|buktikan'
    r'|beri\s+pendapat'
    r'|sejauh\s+mana(?:kah)?'
    r')\b',
    re.IGNORECASE,
)

_RE_SEDERHANA = re.compile(
    r'\b(?:'
    r'mengapa\b'
    r'|kenapa\b'
    r'|bagaimana\b'
    r'|apakah\s+sebab'
    r'|apakah\s+faktor'
    r'|apakah\s+kesan'
    r'|apakah\s+tujuan'
    r'|apakah\s+matlamat'
    r'|apakah\s+langkah'
    r'|terangkan\b'
    r'|huraikan\b'
    r'|jelaskan\b'
    r')\b',
    re.IGNORECASE,
)


def classify_difficulty(stem: str) -> DifficultyLevel:
    """Return 'mudah' | 'sederhana' | 'sukar' based on the question stem."""
    if _RE_SUKAR.search(stem):
        return 'sukar'
    if _RE_SEDERHANA.search(stem):
        return 'sederhana'
    if _RE_MUDAH.search(stem):
        return 'mudah'
    # Default: sederhana (most questions fall into applied understanding)
    return 'sederhana'
