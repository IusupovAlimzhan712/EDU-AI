"""Tests for the AI Tutor module (conversation CRUD + SSE endpoint)."""
import json
import pytest
from unittest.mock import patch

from app.extensions import db
from app.models import Chapter, Topic, TopicPage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_topic(app, email_suffix='tutor'):
    """Create Chapter → Topic → TopicPage and return topic_id."""
    with app.app_context():
        ch = Chapter(form_level=4, chapter_id=1, chapter_name='Bab Satu')
        db.session.add(ch)
        db.session.flush()
        t = Topic(
            form_level=4,
            chapter_id=1,
            topic_name='Tamadun Islam di Madinah',
        )
        db.session.add(t)
        db.session.flush()
        pg = TopicPage(
            topic_id=t.topic_id,
            page_number=1,
            text_content='Tamadun Islam bermula di Madinah pada abad ke-7.',
            word_count=9,
        )
        db.session.add(pg)
        db.session.commit()
        return t.topic_id


def _register_and_auth(client, email='tutor@example.com'):
    body = {
        'email': email,
        'password': 'SecurePass1',
        'fullName': 'Tutor User',
        'formLevel': 4,
    }
    reg = client.post('/api/auth/register', json=body).get_json()
    return {'Authorization': f"Bearer {reg['accessToken']}"}


@pytest.fixture
def setup(app, client):
    topic_id = _seed_topic(app)
    headers = _register_and_auth(client)
    return topic_id, headers


# ---------------------------------------------------------------------------
# GET conversation
# ---------------------------------------------------------------------------

def test_get_conversation_creates_empty(setup, client):
    topic_id, headers = setup
    r = client.get(f'/api/me/topics/{topic_id}/conversation', headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data['topicId'] == topic_id
    assert data['messages'] == []


def test_get_conversation_idempotent(setup, client):
    """Calling GET twice must return the same conversationId."""
    topic_id, headers = setup
    r1 = client.get(f'/api/me/topics/{topic_id}/conversation', headers=headers).get_json()
    r2 = client.get(f'/api/me/topics/{topic_id}/conversation', headers=headers).get_json()
    assert r1['conversationId'] == r2['conversationId']


def test_get_conversation_unknown_topic(client):
    headers = _register_and_auth(client, email='unknown_topic@example.com')
    r = client.get('/api/me/topics/99999/conversation', headers=headers)
    assert r.status_code == 404


def test_get_conversation_requires_auth(setup, client):
    topic_id, _ = setup
    r = client.get(f'/api/me/topics/{topic_id}/conversation')
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# DELETE conversation
# ---------------------------------------------------------------------------

def test_clear_conversation_when_none_exists(setup, client):
    topic_id, headers = setup
    r = client.delete(f'/api/me/topics/{topic_id}/conversation', headers=headers)
    assert r.status_code == 200
    assert 'No conversation' in r.get_json()['message']


def test_clear_conversation_after_get(setup, client):
    """Create then delete — should succeed and return empty messages on next GET."""
    topic_id, headers = setup
    client.get(f'/api/me/topics/{topic_id}/conversation', headers=headers)
    r = client.delete(f'/api/me/topics/{topic_id}/conversation', headers=headers)
    assert r.status_code == 200

    r2 = client.get(f'/api/me/topics/{topic_id}/conversation', headers=headers)
    assert r2.get_json()['messages'] == []


# ---------------------------------------------------------------------------
# POST /messages — input validation (no AI call needed)
# ---------------------------------------------------------------------------

def test_send_message_missing_question(setup, client):
    topic_id, headers = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        json={'currentPage': 1},
        headers=headers,
    )
    assert r.status_code == 400


def test_send_message_empty_question(setup, client):
    topic_id, headers = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        json={'question': '   ', 'currentPage': 1},
        headers=headers,
    )
    assert r.status_code == 400


def test_send_message_page_zero(setup, client):
    topic_id, headers = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        json={'question': 'Apa itu Islam?', 'currentPage': 0},
        headers=headers,
    )
    assert r.status_code == 400


def test_send_message_page_negative(setup, client):
    topic_id, headers = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        json={'question': 'Apa itu Islam?', 'currentPage': -1},
        headers=headers,
    )
    assert r.status_code == 400


def test_send_message_no_body(setup, client):
    topic_id, headers = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        data='not json',
        content_type='text/plain',
        headers=headers,
    )
    assert r.status_code == 400


def test_send_message_requires_auth(setup, client):
    topic_id, _ = setup
    r = client.post(
        f'/api/me/topics/{topic_id}/messages',
        json={'question': 'Test?', 'currentPage': 1},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /messages — SSE streaming (AI mocked)
# ---------------------------------------------------------------------------

def _mock_stream(student_id, topic_id, question, current_page):
    """Minimal valid stream: one token then a final event."""
    yield {'event': 'token', 'chunk': 'Islam '}
    yield {'event': 'token', 'chunk': 'bermula di Madinah.'}
    yield {
        'event': 'final',
        'content': 'Islam bermula di Madinah.',
        'validation_status': 'ok',
        'validation_warning': None,
    }


def test_send_message_streams_sse(setup, client):
    topic_id, headers = setup

    with patch('app.routes.tutor.TutorService.stream_reply', side_effect=_mock_stream):
        r = client.post(
            f'/api/me/topics/{topic_id}/messages',
            json={'question': 'Apa itu tamadun Islam?', 'currentPage': 1},
            headers=headers,
        )

    assert r.status_code == 200
    assert 'text/event-stream' in r.content_type

    raw = r.data.decode()
    assert 'event: token' in raw
    assert 'event: final' in raw
    assert 'Islam bermula di Madinah.' in raw


def test_send_message_warned_response_in_stream(setup, client):
    """A 'warned' validation_status must appear in the SSE final event."""
    topic_id, headers = setup

    def warned_stream(student_id, topic_id, question, current_page):
        yield {
            'event': 'final',
            'content': 'Jawapan tidak disahkan.',
            'validation_status': 'warned',
            'validation_warning': 'Jawapan mungkin tidak berdasarkan teks rujukan.',
        }

    with patch('app.routes.tutor.TutorService.stream_reply', side_effect=warned_stream):
        r = client.post(
            f'/api/me/topics/{topic_id}/messages',
            json={'question': 'Soalan luar skop?', 'currentPage': 1},
            headers=headers,
        )

    assert r.status_code == 200
    raw = r.data.decode()
    assert 'warned' in raw
