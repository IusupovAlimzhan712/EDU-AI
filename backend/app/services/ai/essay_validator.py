"""
Essay question package validators.

Each validator receives the generated package dict and returns a (bool, str)
tuple: (is_valid, reason). The reason is fed back into the generation prompt
on retry so the LLM can self-correct.
"""
import re
from typing import Optional


# SPM-style analysis verbs that signal an open-ended question
_ANALYSIS_VERBS = {
    'bincangkan', 'huraikan', 'jelaskan', 'ulaskan', 'nilaikan',
    'buktikan', 'bandingkan', 'terangkan', 'nyatakan', 'berikan',
    'mengapakah', 'bagaimanakah', 'apakah',
}

# Definition-type openers to reject
_DEFINITION_PATTERNS = re.compile(
    r'^(apakah definisi|takrifkan|nyatakan maksud|berikan definisi)',
    re.IGNORECASE,
)

# Note/point-form line detector
_NOTE_FORM_PATTERN = re.compile(r'^\s*([-•*]|\d+\.|[a-zA-Z]\)|\(\w\))\s')


def _count_tree_nodes(nodes: list) -> int:
    """Recursively count all markable nodes in the unified tree."""
    total = 0
    for node in nodes:
        total += 1
        total += _count_tree_nodes(node.get('children', []))
    return total


def _check_code_sequences(nodes: list, parent_code: str = '') -> Optional[str]:
    """Return an error string if any code sequence has gaps, else None."""
    f_codes = [n for n in nodes if n.get('type') == 'F']
    if f_codes:
        nums = []
        for n in f_codes:
            m = re.search(r'F(\d+)$', n.get('code', ''))
            if m:
                nums.append(int(m.group(1)))
        if nums:
            nums.sort()
            for i in range(len(nums) - 1):
                if nums[i + 1] - nums[i] > 1:
                    return f'Gap in F-code sequence: F{nums[i]} then F{nums[i+1]}'
    for node in nodes:
        children = node.get('children', [])
        if children:
            err = _check_code_sequences(children, node.get('code', ''))
            if err:
                return err
    return None


# ---------------------------------------------------------------------------
# A. Question Quality
# ---------------------------------------------------------------------------

def validate_question_quality(pkg: dict) -> tuple[bool, str]:
    text = (pkg.get('questionText') or '').strip()
    q_type = pkg.get('questionType', '')

    if len(text.split()) < 10:
        return False, 'Question text too short (< 10 words). Write a richer question.'

    if _DEFINITION_PATTERNS.match(text):
        return False, (
            'Question is a definition type (Takrifkan / Apakah definisi). '
            'Write an analysis or evaluation question instead (bincangkan, huraikan, etc.).'
        )

    words_lower = set(text.lower().split())
    if not words_lower & _ANALYSIS_VERBS:
        return False, (
            f'Question lacks an SPM analysis verb. '
            f'Use one of: {", ".join(sorted(_ANALYSIS_VERBS))}.'
        )

    return True, ''


# ---------------------------------------------------------------------------
# B. Marking Scheme Consistency
# ---------------------------------------------------------------------------

def validate_marking_scheme(pkg: dict) -> tuple[bool, str]:
    scheme = pkg.get('markingSchemeJson') or {}
    max_marks = pkg.get('maxMarks', 0)
    q_type = pkg.get('questionType', '')
    nodes = scheme.get('nodes', [])

    if q_type == 'esei':
        ref = scheme.get('referencePoints', [])
        if len(ref) < 4:
            return False, (
                'Essay (esei) marking scheme needs ≥ 4 reference points in referencePoints.'
            )
        return True, ''

    # Struktur
    total_nodes = _count_tree_nodes(nodes)
    if total_nodes < max_marks:
        return False, (
            f'Marking scheme has {total_nodes} markable nodes but maxMarks={max_marks}. '
            f'Add more F/H/C codes so students can reach full marks.'
        )

    gap_err = _check_code_sequences(nodes)
    if gap_err:
        return False, f'Code sequence error: {gap_err}'

    return True, ''


# ---------------------------------------------------------------------------
# C. Model Answer Consistency
# ---------------------------------------------------------------------------

def validate_model_answer(pkg: dict) -> tuple[bool, str]:
    answer = (pkg.get('modelAnswer') or '').strip()
    q_type = pkg.get('questionType', '')
    max_marks = pkg.get('maxMarks', 0)

    min_words = 120 if q_type == 'esei' else 60
    word_count = len(answer.split())
    if word_count < min_words:
        return False, (
            f'Model answer is only {word_count} words; '
            f'minimum is {min_words} for question_type={q_type}.'
        )

    if q_type == 'esei':
        lines = [l for l in answer.split('\n') if l.strip()]
        if lines and sum(1 for l in lines if _NOTE_FORM_PATTERN.match(l)) / len(lines) >= 0.30:
            return False, (
                'Model answer for esei is in note/point form. '
                'Rewrite as continuous prose (prosa berterusan).'
            )

    return True, ''


# ---------------------------------------------------------------------------
# D. Chapter Alignment — lightweight keyword check
# ---------------------------------------------------------------------------

def validate_chapter_alignment(pkg: dict, chapter_texts: list[str]) -> tuple[bool, str]:
    """
    chapter_texts: list of raw text strings from TopicChunk/TopicPage for this chapter.
    Extract nouns from question and verify ≥2 appear in the chapter content.
    """
    q_text = (pkg.get('questionText') or '').lower()
    # Simple noun extraction: words > 5 chars, not stop words
    stopwords = {
        'apakah', 'jelaskan', 'huraikan', 'bincangkan', 'berikan', 'faktor',
        'kesan', 'langkah', 'cara', 'sebab', 'peranan', 'dengan', 'dalam',
        'untuk', 'kepada', 'antara', 'bahawa', 'adalah', 'menjadi',
    }
    q_words = {w for w in re.findall(r'\b\w{5,}\b', q_text) if w not in stopwords}

    combined = ' '.join(chapter_texts).lower()
    matched = [w for w in q_words if w in combined]

    if len(matched) < 2:
        return False, (
            f'Question appears misaligned with chapter content. '
            f'Only {len(matched)} of {len(q_words)} question keywords found in chapter text. '
            f'Ensure the question is about this chapter\'s topics.'
        )
    return True, ''


# ---------------------------------------------------------------------------
# E. Duplicate Detection (Jaccard similarity)
# ---------------------------------------------------------------------------

def validate_not_duplicate(pkg: dict, existing_questions: list[dict]) -> tuple[bool, str]:
    q_words = set(re.findall(r'\b\w+\b', (pkg.get('questionText') or '').lower()))
    for existing in existing_questions:
        ex_words = set(re.findall(r'\b\w+\b', (existing.get('questionText') or '').lower()))
        if not q_words or not ex_words:
            continue
        intersection = q_words & ex_words
        union = q_words | ex_words
        similarity = len(intersection) / len(union)
        if similarity > 0.65:
            return False, (
                f'Question is too similar to an existing question '
                f'(Jaccard={similarity:.2f} > 0.65). Write a distinctly different question.'
            )
    return True, ''


# ---------------------------------------------------------------------------
# Run all validators in sequence
# ---------------------------------------------------------------------------

def validate_package(
    pkg: dict,
    chapter_texts: list[str],
    existing_questions: list[dict],
) -> tuple[bool, str]:
    """
    Run all validators. Returns (True, '') if all pass, else (False, reason).
    """
    for validator, args in [
        (validate_question_quality, (pkg,)),
        (validate_marking_scheme, (pkg,)),
        (validate_model_answer, (pkg,)),
        (validate_chapter_alignment, (pkg, chapter_texts)),
        (validate_not_duplicate, (pkg, existing_questions)),
    ]:
        ok, reason = validator(*args)
        if not ok:
            return False, reason
    return True, ''
