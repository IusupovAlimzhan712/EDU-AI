"""
Unit tests for essay achievement logic.

All tests are pure — no database, no app context required.
The function under test accepts plain dicts so we can construct
any scenario without ORM fixtures.
"""
import pytest
from app.services.achievement_service import compute_essay_achievements


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attempt(question_id: int, score: float, max_score: float = 8.0,
             grading_status: str = 'done') -> dict:
    """Build a minimal attempt dict matching attempt.to_dict() shape."""
    return {
        'questionId': question_id,
        'gradingStatus': grading_status,
        'score': score,
        'maxScore': max_score,
    }


def _ids(achievements: list[dict]) -> set[str]:
    return {a['id'] for a in achievements if a['earned']}


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_returns_six_achievements():
    result = compute_essay_achievements([])
    assert len(result) == 6


def test_all_locked_when_no_attempts():
    result = compute_essay_achievements([])
    assert not any(a['earned'] for a in result)


def test_each_achievement_has_required_keys():
    result = compute_essay_achievements([])
    for a in result:
        assert {'id', 'title', 'description', 'icon', 'earned'} <= a.keys()


# ---------------------------------------------------------------------------
# Completion-count achievements
# ---------------------------------------------------------------------------

def test_essay_beginner_unlocked_at_1():
    attempts = [_attempt(1, 5.0)]
    assert 'essay_beginner' in _ids(compute_essay_achievements(attempts))


def test_essay_beginner_not_unlocked_with_zero():
    assert 'essay_beginner' not in _ids(compute_essay_achievements([]))


def test_essay_writer_unlocked_at_10():
    attempts = [_attempt(q, 4.0) for q in range(1, 11)]
    earned = _ids(compute_essay_achievements(attempts))
    assert 'essay_beginner' in earned
    assert 'essay_writer' in earned


def test_essay_writer_not_unlocked_at_9():
    attempts = [_attempt(q, 4.0) for q in range(1, 10)]
    assert 'essay_writer' not in _ids(compute_essay_achievements(attempts))


def test_essay_expert_unlocked_at_25():
    attempts = [_attempt(q, 4.0) for q in range(1, 26)]
    earned = _ids(compute_essay_achievements(attempts))
    assert 'essay_expert' in earned


def test_essay_expert_not_unlocked_at_24():
    attempts = [_attempt(q, 4.0) for q in range(1, 25)]
    assert 'essay_expert' not in _ids(compute_essay_achievements(attempts))


# ---------------------------------------------------------------------------
# >= 90% high-score achievements
# ---------------------------------------------------------------------------

def test_essay_excellence_unlocked_at_5_high_scores():
    # 5 questions each scored 7.2/8 = 90%
    attempts = [_attempt(q, 7.2, 8.0) for q in range(1, 6)]
    earned = _ids(compute_essay_achievements(attempts))
    assert 'essay_excellence' in earned


def test_essay_excellence_not_unlocked_at_4_high_scores():
    attempts = [_attempt(q, 7.2, 8.0) for q in range(1, 5)]
    assert 'essay_excellence' not in _ids(compute_essay_achievements(attempts))


def test_essay_master_unlocked_at_10_high_scores():
    attempts = [_attempt(q, 7.2, 8.0) for q in range(1, 11)]
    assert 'essay_master' in _ids(compute_essay_achievements(attempts))


def test_spm_essay_elite_unlocked_at_20_high_scores():
    attempts = [_attempt(q, 7.2, 8.0) for q in range(1, 21)]
    assert 'spm_essay_elite' in _ids(compute_essay_achievements(attempts))


def test_spm_essay_elite_not_unlocked_at_19():
    attempts = [_attempt(q, 7.2, 8.0) for q in range(1, 20)]
    assert 'spm_essay_elite' not in _ids(compute_essay_achievements(attempts))


def test_exactly_90_percent_counts_as_high_score():
    # score=6, max_score=6 => exactly 100% — must count
    # score=5.4, max_score=6 => exactly 90% — must count
    attempts = [_attempt(1, 5.4, 6.0)]
    result = compute_essay_achievements(attempts)
    # At 1 high-score attempt, excellence (needs 5) should not fire
    assert 'essay_beginner' in _ids(result)
    assert 'essay_excellence' not in _ids(result)


def test_89_percent_does_not_count_as_high_score():
    # 7.1 / 8 = 88.75% — should NOT count toward high-score tier
    attempts = [_attempt(q, 7.1, 8.0) for q in range(1, 6)]
    assert 'essay_excellence' not in _ids(compute_essay_achievements(attempts))


# ---------------------------------------------------------------------------
# Best-attempt logic (duplicate attempts on same question)
# ---------------------------------------------------------------------------

def test_duplicate_attempts_count_once_for_completion():
    # 3 attempts on question 1, 0 on any other — should count as 1 completed
    attempts = [
        _attempt(1, 3.0),
        _attempt(1, 4.0),
        _attempt(1, 5.0),
    ]
    result = compute_essay_achievements(attempts)
    # Essay Beginner (1 needed) → earned; Essay Writer (10 needed) → not earned
    assert 'essay_beginner' in _ids(result)
    assert 'essay_writer' not in _ids(result)


def test_best_score_used_for_high_score_threshold():
    # Early attempt scored 50%, later attempt scored 90% on same question
    attempts = [
        _attempt(1, 4.0, 8.0),   # 50%
        _attempt(1, 7.2, 8.0),   # 90% ← best
    ]
    # 4 more questions at 90% to meet essay_excellence threshold of 5
    for q in range(2, 6):
        attempts.append(_attempt(q, 7.2, 8.0))

    assert 'essay_excellence' in _ids(compute_essay_achievements(attempts))


def test_best_score_low_attempt_does_not_override_high():
    # First attempt 90%, second attempt 10% on same question
    attempts = [
        _attempt(1, 7.2, 8.0),   # 90% ← best kept
        _attempt(1, 0.8, 8.0),   # 10% — should NOT replace best
    ]
    for q in range(2, 6):
        attempts.append(_attempt(q, 7.2, 8.0))

    assert 'essay_excellence' in _ids(compute_essay_achievements(attempts))


def test_mix_of_duplicate_and_unique_completion():
    # 5 unique questions + 3 re-attempts on question 1 → completed=5
    attempts = [_attempt(q, 4.0) for q in range(1, 6)]
    attempts += [_attempt(1, 5.0), _attempt(1, 3.0)]
    result = compute_essay_achievements(attempts)
    assert 'essay_beginner' in _ids(result)
    assert 'essay_writer' not in _ids(result)  # only 5, not 10


# ---------------------------------------------------------------------------
# Non-graded attempts are ignored
# ---------------------------------------------------------------------------

def test_pending_attempts_ignored():
    attempts = [_attempt(1, 5.0, grading_status='pending')]
    assert not any(a['earned'] for a in compute_essay_achievements(attempts))


def test_grading_failed_attempts_ignored():
    attempts = [_attempt(1, 5.0, grading_status='failed')]
    assert not any(a['earned'] for a in compute_essay_achievements(attempts))


def test_submitted_but_not_graded_ignored():
    attempts = [_attempt(1, 5.0, grading_status='grading')]
    assert not any(a['earned'] for a in compute_essay_achievements(attempts))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_zero_score_still_counts_as_completed():
    # Completing an essay with 0/8 is still a graded completion
    attempts = [_attempt(1, 0.0)]
    assert 'essay_beginner' in _ids(compute_essay_achievements(attempts))


def test_zero_score_does_not_count_as_high_score():
    attempts = [_attempt(q, 0.0) for q in range(1, 6)]
    assert 'essay_excellence' not in _ids(compute_essay_achievements(attempts))


def test_none_score_attempt_skipped():
    attempts = [{'questionId': 1, 'gradingStatus': 'done', 'score': None, 'maxScore': 8}]
    assert not any(a['earned'] for a in compute_essay_achievements(attempts))


def test_zero_max_score_attempt_skipped():
    attempts = [{'questionId': 1, 'gradingStatus': 'done', 'score': 5.0, 'maxScore': 0}]
    assert not any(a['earned'] for a in compute_essay_achievements(attempts))
