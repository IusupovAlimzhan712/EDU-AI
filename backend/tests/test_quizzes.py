"""Tests for the Quiz module (current design: AI-generated per-attempt questions)."""
import json
import pytest
from unittest.mock import patch
from collections import Counter

from app.extensions import db
from app.models import Chapter, Topic, Quiz, AttemptQuestion, QuizAttempt
from app.repositories import AttemptQuestionRepository


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_quiz_app(app):
    """Create one chapter, one topic, and one quiz template (no pre-seeded questions)."""
    with app.app_context():
        db.session.add(Chapter(form_level=4, chapter_id=1, chapter_name='Warisan Negara Bangsa'))
        db.session.commit()
        db.session.add(Topic(
            form_level=4, chapter_id=1, topic_name='Asal Usul Negara Bangsa'
        ))
        db.session.add(Quiz(
            form_level=4, chapter_id=1, scope='bab', source='seed',
            title='Test Quiz Bab 1', default_question_count=5,
        ))
        db.session.commit()
    return app


def _auth_header(client, email='quiz_taker@example.com'):
    reg = client.post('/api/auth/register', json={
        'email': email,
        'password': 'SecurePass1',
        'fullName': 'Quiz Taker',
        'formLevel': 4,
    }).get_json()
    headers = {'Authorization': f"Bearer {reg['accessToken']}"}
    # Complete all seeded topics so the chapter is unlocked for quiz access
    topics = client.get('/api/topics?formLevel=4&chapterId=1', headers=headers).get_json() or []
    for t in topics:
        client.post(f"/api/topics/{t['topicId']}/complete", headers=headers)
    return headers


def _seed_questions(app, attempt_id: int, n: int = 5):
    """Manually add n AttemptQuestion rows and mark the attempt ready.

    Correct answer is always index 0. Used to skip AI generation in tests
    that need questions to exist (answer-save, submit, review).
    """
    with app.app_context():
        for i in range(1, n + 1):
            db.session.add(AttemptQuestion(
                attempt_id=attempt_id,
                order_index=i,
                stem=f'Soalan {i}?',
                options=['Betul', 'Salah A', 'Salah B', 'Salah C'],
                correct_index=0,
                explanation='Sebab betul.',
                points=1,
            ))
        attempt = db.session.get(QuizAttempt, attempt_id)
        attempt.generation_status = 'ready'
        db.session.commit()


# ---------------------------------------------------------------------------
# List quizzes
# ---------------------------------------------------------------------------

def test_list_quizzes_empty_progress(seeded_quiz_app, client):
    headers = _auth_header(client)
    r = client.get('/api/quizzes', headers=headers)
    assert r.status_code == 200
    quizzes = r.get_json()
    assert len(quizzes) == 1
    q = quizzes[0]
    assert q['defaultQuestionCount'] == 5
    assert q['hasInProgressAttempt'] is False
    assert q['bestScore'] is None
    assert q['attemptCount'] == 0


def test_list_quizzes_requires_auth(seeded_quiz_app, client):
    r = client.get('/api/quizzes')
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Start attempt
# ---------------------------------------------------------------------------

def test_start_attempt_creates_pending(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']

    r = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers)
    assert r.status_code == 201
    attempt = r.get_json()
    assert attempt['status'] == 'in_progress'
    assert attempt['generationStatus'] == 'pending'
    assert attempt['questions'] == []


def test_start_attempt_resumes_in_progress(seeded_quiz_app, client):
    """Starting a quiz twice must resume the same attempt."""
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']

    r1 = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers).get_json()
    r2 = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers).get_json()
    assert r1['attemptId'] == r2['attemptId']


def test_start_attempt_shows_in_quiz_list(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers).get_json()['attemptId']
    # Seed questions and mark ready so the attempt is resumable from the list
    _seed_questions(seeded_quiz_app, attempt_id, n=3)

    quizzes = client.get('/api/quizzes', headers=headers).get_json()
    assert quizzes[0]['hasInProgressAttempt'] is True
    assert quizzes[0]['inProgressAttemptId'] is not None


# ---------------------------------------------------------------------------
# Stream questions (SSE) — AI mocked
# ---------------------------------------------------------------------------

def _mock_stream_generator(student_id, attempt_id):
    yield {
        'event': 'question',
        'question': {
            'attemptQuestionId': 999,
            'orderIndex': 1,
            'stem': 'Siapakah pengasas Melaka?',
            'options': ['Parameswara', 'Tun Perak', 'Sultan Mahmud', 'Bendahara'],
            'points': 1,
        },
    }
    yield {'event': 'done', 'total': 1, 'target': 5}


def test_stream_questions_returns_sse(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    with patch(
        'app.routes.quizzes.QuizService.stream_questions',
        side_effect=_mock_stream_generator,
    ):
        r = client.get(f'/api/me/attempts/{attempt_id}/stream', headers=headers)

    assert r.status_code == 200
    assert 'text/event-stream' in r.content_type
    raw = r.data.decode()
    assert 'event: question' in raw
    assert 'event: done' in raw
    assert 'Parameswara' in raw


def test_stream_questions_requires_auth(seeded_quiz_app, client):
    headers = _auth_header(client, email='stream_noauth@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    r = client.get(f'/api/me/attempts/{attempt_id}/stream')
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Save answer
# ---------------------------------------------------------------------------

def test_save_answer_success(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    _seed_questions(seeded_quiz_app, attempt_id, n=3)

    # Fetch the attempt to get a real attemptQuestionId
    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    first_q_id = attempt['questions'][0]['attemptQuestionId']

    r = client.patch(
        f'/api/me/attempts/{attempt_id}/answers',
        json={'attemptQuestionId': first_q_id, 'selectedIndex': 0},
        headers=headers,
    )
    assert r.status_code == 200
    ans = r.get_json()
    assert ans['selectedIndex'] == 0


def test_save_answer_mid_attempt_hides_correct(seeded_quiz_app, client):
    """Student must not see correctIndex during an in-progress attempt."""
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=1)

    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    assert 'correctIndex' not in attempt['questions'][0]


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def test_submit_attempt_grades_correctly(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=5)

    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    questions = attempt['questions']

    # Answer 4 correctly (index 0 = correct), 1 wrong (index 1)
    for i, q in enumerate(questions):
        selected = 0 if i < 4 else 1
        client.patch(
            f'/api/me/attempts/{attempt_id}/answers',
            json={'attemptQuestionId': q['attemptQuestionId'], 'selectedIndex': selected},
            headers=headers,
        )

    r = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    assert r.status_code == 200
    result = r.get_json()
    assert result['status'] == 'submitted'
    assert result['correctCount'] == 4
    assert result['totalQuestions'] == 5
    assert result['score'] == 4
    assert result['maxScore'] == 5
    assert 'correctIndex' in result['questions'][0]


def test_submit_idempotent(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=2)

    r1 = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    r2 = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_json()['attemptId'] == r2.get_json()['attemptId']


def test_submit_no_questions_rejected(seeded_quiz_app, client):
    """Submitting before any questions are generated must fail."""
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    r = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    assert r.status_code == 422


def test_save_answer_after_submit_forbidden(seeded_quiz_app, client):
    headers = _auth_header(client)
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=1)

    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    q_id = attempt['questions'][0]['attemptQuestionId']

    client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)

    r = client.patch(
        f'/api/me/attempts/{attempt_id}/answers',
        json={'attemptQuestionId': q_id, 'selectedIndex': 0},
        headers=headers,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cross-student ownership
# ---------------------------------------------------------------------------

def test_attempt_owned_by_another_student_forbidden(seeded_quiz_app, client):
    h1 = _auth_header(client, email='student1@example.com')
    quiz_id = client.get('/api/quizzes', headers=h1).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=h1
    ).get_json()['attemptId']

    h2 = _auth_header(client, email='student2@example.com')
    r = client.get(f'/api/me/attempts/{attempt_id}', headers=h2)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# List my attempts
# ---------------------------------------------------------------------------

def test_list_my_attempts_empty(seeded_quiz_app, client):
    headers = _auth_header(client, email='no_attempts@example.com')
    r = client.get('/api/me/attempts', headers=headers)
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_my_attempts_requires_auth(seeded_quiz_app, client):
    r = client.get('/api/me/attempts')
    assert r.status_code == 401


def test_list_my_attempts_after_start(seeded_quiz_app, client):
    headers = _auth_header(client, email='lister@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers)

    r = client.get('/api/me/attempts', headers=headers)
    assert r.status_code == 200
    attempts = r.get_json()
    assert len(attempts) == 1
    assert attempts[0]['status'] == 'in_progress'


def test_list_my_attempts_filter_by_quiz_id(seeded_quiz_app, client):
    headers = _auth_header(client, email='quiz_filter@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers)

    r = client.get(f'/api/me/attempts?quiz_id={quiz_id}', headers=headers)
    assert r.status_code == 200
    assert len(r.get_json()) == 1

    r2 = client.get('/api/me/attempts?quiz_id=99999', headers=headers)
    assert r2.status_code == 200
    assert r2.get_json() == []


def test_list_my_attempts_isolation_between_students(seeded_quiz_app, client):
    """Each student sees only their own attempts."""
    h1 = _auth_header(client, email='iso_a@example.com')
    h2 = _auth_header(client, email='iso_b@example.com')
    quiz_id = client.get('/api/quizzes', headers=h1).get_json()[0]['quizId']

    client.post(f'/api/quizzes/{quiz_id}/attempts', headers=h1)
    client.post(f'/api/quizzes/{quiz_id}/attempts', headers=h2)

    a1 = client.get('/api/me/attempts', headers=h1).get_json()
    a2 = client.get('/api/me/attempts', headers=h2).get_json()
    assert len(a1) == 1
    assert len(a2) == 1
    assert a1[0]['attemptId'] != a2[0]['attemptId']


# ---------------------------------------------------------------------------
# 404 / not-found paths
# ---------------------------------------------------------------------------

def test_start_attempt_nonexistent_quiz(seeded_quiz_app, client):
    headers = _auth_header(client, email='notfound_quiz@example.com')
    r = client.post('/api/quizzes/99999/attempts', headers=headers)
    assert r.status_code == 404


def test_get_attempt_nonexistent(seeded_quiz_app, client):
    headers = _auth_header(client, email='notfound_attempt@example.com')
    r = client.get('/api/me/attempts/99999', headers=headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# selectedIndex validation (boundary tests)
# ---------------------------------------------------------------------------

def test_save_answer_null_selected_index(seeded_quiz_app, client):
    """null selectedIndex is valid — it means the student un-answered the question."""
    headers = _auth_header(client, email='null_ans@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=1)

    q_id = client.get(
        f'/api/me/attempts/{attempt_id}', headers=headers
    ).get_json()['questions'][0]['attemptQuestionId']

    r = client.patch(
        f'/api/me/attempts/{attempt_id}/answers',
        json={'attemptQuestionId': q_id, 'selectedIndex': None},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.get_json()['selectedIndex'] is None


def test_save_answer_negative_index_rejected(seeded_quiz_app, client):
    headers = _auth_header(client, email='neg_idx@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=1)

    q_id = client.get(
        f'/api/me/attempts/{attempt_id}', headers=headers
    ).get_json()['questions'][0]['attemptQuestionId']

    r = client.patch(
        f'/api/me/attempts/{attempt_id}/answers',
        json={'attemptQuestionId': q_id, 'selectedIndex': -1},
        headers=headers,
    )
    assert r.status_code == 422


def test_save_answer_out_of_range_index_rejected(seeded_quiz_app, client):
    headers = _auth_header(client, email='oob_idx@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=1)

    q_id = client.get(
        f'/api/me/attempts/{attempt_id}', headers=headers
    ).get_json()['questions'][0]['attemptQuestionId']

    r = client.patch(
        f'/api/me/attempts/{attempt_id}/answers',
        json={'attemptQuestionId': q_id, 'selectedIndex': 4},
        headers=headers,
    )
    assert r.status_code == 422


def test_save_answer_cross_attempt_injection_rejected(seeded_quiz_app, client):
    """Student B cannot save an answer using Student A's attemptQuestionId."""
    h1 = _auth_header(client, email='inject_owner@example.com')
    h2 = _auth_header(client, email='inject_attacker@example.com')
    quiz_id = client.get('/api/quizzes', headers=h1).get_json()[0]['quizId']

    aid1 = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=h1).get_json()['attemptId']
    aid2 = client.post(f'/api/quizzes/{quiz_id}/attempts', headers=h2).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, aid1, n=1)
    _seed_questions(seeded_quiz_app, aid2, n=1)

    q_from_aid1 = client.get(
        f'/api/me/attempts/{aid1}', headers=h1
    ).get_json()['questions'][0]['attemptQuestionId']

    # Attacker tries to submit Student A's question ID against their own attempt
    r = client.patch(
        f'/api/me/attempts/{aid2}/answers',
        json={'attemptQuestionId': q_from_aid1, 'selectedIndex': 0},
        headers=h2,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# quiz list — form_level filter + progress fields
# ---------------------------------------------------------------------------

def test_list_quizzes_form_level_filter(seeded_quiz_app, client):
    headers = _auth_header(client, email='filter_user@example.com')
    r = client.get('/api/quizzes?form_level=4', headers=headers)
    assert r.status_code == 200
    quizzes = r.get_json()
    assert len(quizzes) == 1
    assert quizzes[0]['formLevel'] == 4


def test_list_quizzes_wrong_form_level_returns_empty(seeded_quiz_app, client):
    headers = _auth_header(client, email='filter_empty@example.com')
    r = client.get('/api/quizzes?form_level=5', headers=headers)
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_quizzes_invalid_form_level_rejected(seeded_quiz_app, client):
    headers = _auth_header(client, email='filter_bad@example.com')
    r = client.get('/api/quizzes?form_level=abc', headers=headers)
    assert r.status_code == 400


def test_list_quizzes_best_score_after_submit(seeded_quiz_app, client):
    headers = _auth_header(client, email='best_score@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=4)

    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    for q in attempt['questions']:
        client.patch(
            f'/api/me/attempts/{attempt_id}/answers',
            json={'attemptQuestionId': q['attemptQuestionId'], 'selectedIndex': 0},
            headers=headers,
        )
    client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)

    quizzes = client.get('/api/quizzes', headers=headers).get_json()
    assert quizzes[0]['bestScore'] == 4
    assert quizzes[0]['bestPercentage'] == 100.0
    assert quizzes[0]['attemptCount'] == 1
    assert quizzes[0]['hasInProgressAttempt'] is False


# ---------------------------------------------------------------------------
# Submit edge cases
# ---------------------------------------------------------------------------

def test_submit_all_unanswered_scores_zero(seeded_quiz_app, client):
    """Submitting without answering any question must score 0, not error."""
    headers = _auth_header(client, email='no_ans@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=3)

    r = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    assert r.status_code == 200
    result = r.get_json()
    assert result['correctCount'] == 0
    assert result['score'] == 0
    assert result['totalQuestions'] == 3
    assert result['status'] == 'submitted'


def test_submit_partial_answers_grades_correctly(seeded_quiz_app, client):
    """Only answered questions with correct index are counted as correct."""
    headers = _auth_header(client, email='partial_ans@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']
    _seed_questions(seeded_quiz_app, attempt_id, n=4)

    attempt = client.get(f'/api/me/attempts/{attempt_id}', headers=headers).get_json()
    questions = attempt['questions']

    # Answer only first 2 (correctly), leave last 2 unanswered
    for q in questions[:2]:
        client.patch(
            f'/api/me/attempts/{attempt_id}/answers',
            json={'attemptQuestionId': q['attemptQuestionId'], 'selectedIndex': 0},
            headers=headers,
        )

    r = client.post(f'/api/me/attempts/{attempt_id}/submit', headers=headers)
    result = r.get_json()
    assert result['correctCount'] == 2
    assert result['score'] == 2
    assert result['totalQuestions'] == 4


# ---------------------------------------------------------------------------
# Answer shuffle — AttemptQuestionRepository.add() correctness contract
# ---------------------------------------------------------------------------

def test_shuffle_preserves_correct_option(seeded_quiz_app, client):
    """add() must shuffle options and update correct_index so the stored correct
    option (by value) is always what the LLM chose, regardless of position."""
    options = ['Alpha', 'Beta', 'Gamma', 'Delta']
    # Register a student and start an attempt to get a valid attempt_id
    headers = _auth_header(client, email='shuffle_check@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    with seeded_quiz_app.app_context():
        for original_correct in range(4):
            aq = AttemptQuestionRepository.add(
                attempt_id=attempt_id,
                order_index=original_correct + 1,
                stem=f'Soalan shuffle {original_correct}?',
                options=options[:],
                correct_index=original_correct,
                explanation='Test.',
            )
            db.session.commit()
            expected_value = options[original_correct]
            assert aq.options[aq.correct_index] == expected_value, (
                f"original_correct={original_correct}: "
                f"expected '{expected_value}' at stored index {aq.correct_index}, "
                f"got '{aq.options[aq.correct_index]}'. options={aq.options}"
            )


def test_shuffle_produces_uniform_distribution_over_many_calls(seeded_quiz_app, client):
    """Over 200 add() calls with correct_index=0, the stored correct_index
    should be roughly uniformly distributed across 0-3.  This catches
    the pre-fix bug where A was dominant (>50% without shuffle)."""
    options = ['Correct', 'Wrong1', 'Wrong2', 'Wrong3']
    distribution = Counter()

    headers = _auth_header(client, email='shuffle_dist@example.com')
    quiz_id = client.get('/api/quizzes', headers=headers).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=headers
    ).get_json()['attemptId']

    with seeded_quiz_app.app_context():
        for i in range(200):
            aq = AttemptQuestionRepository.add(
                attempt_id=attempt_id,
                order_index=i + 1,
                stem=f'Soalan {i}?',
                options=options[:],
                correct_index=0,
                explanation='Test.',
            )
            db.session.commit()
            distribution[aq.correct_index] += 1

    total = sum(distribution.values())
    # Each position should get ~25% ± 15% (loose threshold).
    # Pre-fix: A would be ~57%+ which would fail easily.
    for idx in range(4):
        pct = distribution[idx] / total * 100
        assert pct > 10, (
            f"correct_index={idx} appeared only {pct:.1f}% of the time — "
            f"shuffle is not working. Distribution: {dict(distribution)}"
        )
        assert pct < 50, (
            f"correct_index={idx} appeared {pct:.1f}% of the time — "
            f"strongly biased. Distribution: {dict(distribution)}"
        )


# ---------------------------------------------------------------------------
# SSE stream — cross-student access via stream endpoint
# ---------------------------------------------------------------------------

def test_stream_attempt_other_student_returns_sse_error(seeded_quiz_app, client):
    """Cross-student stream access: ownership error must surface as SSE error event."""
    h1 = _auth_header(client, email='stream_own@example.com')
    quiz_id = client.get('/api/quizzes', headers=h1).get_json()[0]['quizId']
    attempt_id = client.post(
        f'/api/quizzes/{quiz_id}/attempts', headers=h1
    ).get_json()['attemptId']

    h2 = _auth_header(client, email='stream_steal@example.com')
    r = client.get(f'/api/me/attempts/{attempt_id}/stream', headers=h2)

    # SSE route wraps ForbiddenError in an error event (still HTTP 200)
    assert r.status_code == 200
    raw = r.data.decode()
    assert 'event: error' in raw
