"""
Pure achievement-computation functions.

No DB queries — callers pass pre-fetched data as plain dicts so this
module is trivially unit-testable without a database or app context.
"""


def compute_essay_achievements(essay_attempts: list[dict]) -> list[dict]:
    """Derive essay achievements from a student's graded attempts.

    Rules:
    - Only 'done' (graded) attempts count.
    - Uses best score per unique questionId — multiple attempts on the
      same question do not inflate counts.
    - Completion count = number of distinct questions with ≥1 graded attempt.
    - High-score count = number of distinct questions where best score ≥ 90 %.
    """
    best_pct: dict[int, float] = {}
    for a in essay_attempts:
        if a.get('gradingStatus') != 'done':
            continue
        score = a.get('score')
        max_score = a.get('maxScore')
        if score is None or not max_score or max_score <= 0:
            continue
        pct = score / max_score * 100
        q_id = a['questionId']
        if pct > best_pct.get(q_id, -1):
            best_pct[q_id] = pct

    completed = len(best_pct)
    high_score = sum(1 for p in best_pct.values() if p >= 90)

    return [
        {
            'id': 'essay_beginner',
            'title': 'Essay Beginner',
            'description': 'Complete 1 essay',
            'icon': '✏️',
            'earned': completed >= 1,
        },
        {
            'id': 'essay_writer',
            'title': 'Essay Writer',
            'description': 'Complete 10 essays',
            'icon': '📝',
            'earned': completed >= 10,
        },
        {
            'id': 'essay_expert',
            'title': 'Essay Expert',
            'description': 'Complete 25 essays',
            'icon': '📚',
            'earned': completed >= 25,
        },
        {
            'id': 'essay_excellence',
            'title': 'Essay Excellence',
            'description': 'Score ≥ 90% on 5 essays',
            'icon': '⭐',
            'earned': high_score >= 5,
        },
        {
            'id': 'essay_master',
            'title': 'Essay Master',
            'description': 'Score ≥ 90% on 10 essays',
            'icon': '🏆',
            'earned': high_score >= 10,
        },
        {
            'id': 'spm_essay_elite',
            'title': 'SPM Essay Elite',
            'description': 'Score ≥ 90% on 20 essays',
            'icon': '👑',
            'earned': high_score >= 20,
        },
    ]
