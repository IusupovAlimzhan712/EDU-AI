"""Tests for the Quiz module (current design: AI-generated per-attempt questions)."""
import json
import pytest
from unittest.mock import patch

from app.extensions import db
from app.models import Chapter, Quiz, AttemptQuestion, QuizAttempt


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_quiz_app(app):
    """Create one chapter and one quiz template (no pre-seeded questions)."""
    with app.app_context():
        db.session.add(Chapter(form_level=4, chapter_id=1, chapter_name='Warisan Negara Bangsa'))
        db.session.commit()
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
    return {'Authorization': f"Bearer {reg['accessToken']}"}


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
    client.post(f'/api/quizzes/{quiz_id}/attempts', headers=headers)

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
