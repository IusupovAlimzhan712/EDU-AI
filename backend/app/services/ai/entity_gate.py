"""
Entity Absence Gate — deterministic pre-generation check.

Before calling the LLM, detect what kind of entity the question expects
(person name, date/year, place, law/act, event) and check whether the
retrieved context actually contains that kind of entity. If not, return
an uncertainty response immediately without any LLM invocation.

This eliminates the "Funan ruler" class of hallucinations — questions
about entities that are simply absent from the retrieved pages.
"""
import re
import logging
from typing import Literal

logger = logging.getLogger(__name__)

EntityType = Literal['person', 'date', 'place', 'law', 'event', 'none']

UNCERTAINTY_RESPONSE = (
    'Berdasarkan teks rujukan yang ada, maklumat tersebut tidak dinyatakan '
    'secara jelas. Sila rujuk bab yang berkaitan atau tanya soalan yang lebih spesifik.'
)

# ── Detection patterns ─────────────────────────────────────────────────────

_RE_PERSON = re.compile(
    r'\b(?:'
    r'siapa(?:kah)?'
    r'|nama\s+(?:raja|sultan|pemimpin|tokoh|orang|ketua|gabenor|pengarah)'
    r'|(?:raja|sultan|pemimpin|tokoh|pahlawan|wira)\s+(?:yang|ialah|adalah)'
    r'|siapakah\s+(?:yang|orang)'
    r')\b',
    re.IGNORECASE,
)

_RE_DATE = re.compile(
    r'\b(?:'
    r'bila(?:kah)?'
    r'|tahun\s+(?:berapa|mana|bila)'
    r'|pada\s+(?:tahun|tarikh|hari)'
    r'|tarikh\s+(?:apa|berapa|bila)'
    r'|(?:berapa|yang\s+ke-?\d+)\s+tahun'
    r')\b',
    re.IGNORECASE,
)

_RE_PLACE = re.compile(
    r'\b(?:'
    r'di\s+mana'
    r'|tempat\s+(?:apa|mana|yang)'
    r'|(?:ibu\s+kota|negara|bandar|kawasan|lokasi)\s+(?:apa|mana|yang)'
    r'|di\s+(?:negeri|negara|bandar|kawasan)\s+mana'
    r')\b',
    re.IGNORECASE,
)

_RE_LAW = re.compile(
    r'\b(?:'
    r'akta\s+(?:apa|mana|yang)'
    r'|perjanjian\s+(?:apa|mana|yang)'
    r'|undang.undang\s+(?:apa|mana|yang)'
    r'|dasar\s+(?:apa|mana|yang)'
    r'|(?:akta|perjanjian|undang.undang)\s+\w+\s+(?:ialah|adalah|bermaksud)'
    r')\b',
    re.IGNORECASE,
)

_RE_EVENT = re.compile(
    r'\b(?:'
    r'peristiwa\s+(?:apa|mana|yang)'
    r'|kejadian\s+(?:apa|mana)'
    r'|apa(?:kah)?\s+(?:peristiwa|kejadian|sebab|faktor|tujuan|matlamat)'
    r'|mengapa\b'
    r'|kenapa\b'
    r'|jelaskan\s+(?:peristiwa|sebab|faktor|langkah|proses)'
    r')\b',
    re.IGNORECASE,
)

# ── Context presence patterns ──────────────────────────────────────────────

# Multi-word capitalized name sequence — more likely a person name than a place
_RE_MULTI_WORD_NAME = re.compile(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b')

# BM personal pronouns — strong signal that context mentions a specific person
_RE_PERSONAL_PRONOUN = re.compile(
    r'\b(?:beliau|baginda|baginda|dia|mereka)\b', re.IGNORECASE
)

# Person title prefixes common in Malaysian history
_RE_PERSON_TITLE = re.compile(
    r'\b(?:Raja|Sultan|Tun|Dato|Datuk|Bendahara|Temenggung|Laksamana|Yamtuan)\b'
)

# Any 4-digit year 1000–1999
_RE_YEAR = re.compile(r'\b1[0-9]{3}\b')

# Known place indicators: Tanah Melayu, Malaya, Malaysia, any capitalized
# two-word compound, or common place suffixes
_RE_PLACE_PRESENCE = re.compile(
    r'\b(?:'
    r'Tanah\s+Melayu'
    r'|Malaya\b'
    r'|Malaysia\b'
    r'|Singapura\b'
    r'|Melaka\b'
    r'|Perak\b'
    r'|Selangor\b'
    r'|Pahang\b'
    r'|Johor\b'
    r'|Kedah\b'
    r'|Kelantan\b'
    r'|Terengganu\b'
    r'|Borneo\b'
    r'|Sabah\b'
    r'|Sarawak\b'
    r'|Pulau\s+Pinang\b'
    r'|Negeri\s+Sembilan\b'
    r'|Perlis\b'
    r'|Labuan\b'
    r')\b',
    re.IGNORECASE,
)

# Legal/policy document markers — require capitalized form (specific legislation, not generic terms)
_RE_LAW_PRESENCE = re.compile(
    r'\b(?:Akta|Perjanjian|Undang-Undang|Dasar|Kanun|Perlembagaan)\b',
)

# Event markers — action/process vocabulary abundant in historical text
_RE_EVENT_PRESENCE = re.compile(
    r'\b(?:berlaku|terjadi|peristiwa|kejadian|pemberontakan|serangan|penaklukan'
    r'|kemerdekaan|pendudukan|perjuangan|rundingan|perjanjian)\b',
    re.IGNORECASE,
)


def detect_expected_entity_type(question: str) -> EntityType:
    """Return the entity type the question is looking for, or 'none'."""
    q = question.strip()
    if _RE_PERSON.search(q):
        return 'person'
    if _RE_DATE.search(q):
        return 'date'
    if _RE_PLACE.search(q):
        return 'place'
    if _RE_LAW.search(q):
        return 'law'
    if _RE_EVENT.search(q):
        return 'event'
    return 'none'


def context_has_entity(entity_type: EntityType, context: str) -> bool:
    """Return True if context plausibly contains the expected entity type."""
    if entity_type in ('none', 'event'):
        # 'none' — no specific entity required; 'event' — explanation questions
        # are too open-ended to gate on specific event vocabulary.
        return True

    if entity_type == 'person':
        # Require a personal pronoun (beliau/baginda/dia) OR a person-title prefix.
        # Multi-word names are not used here because place names like "Selat Melaka"
        # would cause false passes.
        return bool(
            _RE_PERSONAL_PRONOUN.search(context)
            or _RE_PERSON_TITLE.search(context)
        )

    if entity_type == 'date':
        return bool(_RE_YEAR.search(context))

    if entity_type == 'place':
        return bool(_RE_PLACE_PRESENCE.search(context) or _RE_MULTI_WORD_NAME.search(context))

    if entity_type == 'law':
        return bool(_RE_LAW_PRESENCE.search(context))

    return True


def check_entity_gate(question: str, context: str) -> bool:
    """Return True if LLM should proceed, False if answer should be the uncertainty response.

    False means: the question expects an entity that is absent from context.
    """
    entity_type = detect_expected_entity_type(question)
    present = context_has_entity(entity_type, context)

    if not present:
        logger.info(
            'Entity gate blocked: expected=%s not found in context (%d chars)',
            entity_type, len(context),
        )

    return present
