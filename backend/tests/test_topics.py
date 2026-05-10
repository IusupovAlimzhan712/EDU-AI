"""Sanity tests for the Topic module (Week 3-4 deliverable)."""
import pytest

from app.extensions import db
from app.models import Chapter, Topic


@pytest.fixture
def seeded_app(app):
    """Add a handful of chapters + topics so the topic endpoints have data."""
    with app.app_context():
        db.session.add_all([
            Chapter(form_level=4, chapter_id=1, chapter_name='Tamadun Awal'),
            Chapter(form_level=5, chapter_id=1, chapter_name='Warisan Negara'),
        ])
        db.session.commit()
        db.session.add_all([
            Topic(form_level=4, chapter_id=1, topic_name='Zaman Prasejarah',
                  content='Lorem ipsum'),
            Topic(form_level=4, chapter_id=1, topic_name='Zaman Neolitik',
                  content='Lorem ipsum'),
            Topic(form_level=5, chapter_id=1, topic_name='Konsep Negara',
                  content='Lorem ipsum'),
        ])
        db.session.commit()
    return app


def _auth_header(client, email='topic_user@example.com'):
    body = {
        'email': email,
        'password': 'SecurePass1',
        'fullName': 'Topic User',
        'formLevel': 4,
    }
    reg = client.post('/api/auth/register', json=body).get_json()
    return {'Authorization': f"Bearer {reg['accessToken']}"}


def test_list_chapters(seeded_app, client):
    headers = _auth_header(client)
    r = client.get('/api/chapters', headers=headers)
    assert r.status_code == 200
    chapters = r.get_json()
    assert len(chapters) == 2


def test_list_chapters_filtered(seeded_app, client):
    headers = _auth_header(client)
    r = client.get('/api/chapters?form_level=4', headers=headers)
    assert r.status_code == 200
    chapters = r.get_json()
    assert all(c['formLevel'] == 4 for c in chapters)


def test_list_topics(seeded_app, client):
    headers = _auth_header(client)
    r = client.get('/api/topics?form_level=4', headers=headers)
    assert r.status_code == 200
    items = r.get_json()
    assert len(items) == 2
    assert all('isBookmarked' in t and 'isCompleted' in t for t in items)


def test_bookmark_toggle(seeded_app, client):
    headers = _auth_header(client)
    topic_id = client.get('/api/topics', headers=headers).get_json()[0]['topicId']

    r = client.post(f'/api/topics/{topic_id}/bookmark', headers=headers)
    assert r.status_code == 201

    r = client.get('/api/me/bookmarks', headers=headers)
    assert r.status_code == 200
    assert len(r.get_json()) == 1

    r = client.delete(f'/api/topics/{topic_id}/bookmark', headers=headers)
    assert r.status_code == 200
    assert len(client.get('/api/me/bookmarks', headers=headers).get_json()) == 0


def test_complete_toggle_and_progress(seeded_app, client):
    headers = _auth_header(client)
    topics = client.get('/api/topics', headers=headers).get_json()
    topic_id = topics[0]['topicId']

    assert client.post(f'/api/topics/{topic_id}/complete', headers=headers).status_code == 201

    r = client.get('/api/me/progress', headers=headers)
    assert r.status_code == 200
    progress = r.get_json()
    assert progress['completedTopicsCount'] == 1
    assert progress['totalTopics'] == 3
    assert progress['completionRate'] > 0


def test_topic_detail_includes_status(seeded_app, client):
    headers = _auth_header(client)
    topic_id = client.get('/api/topics', headers=headers).get_json()[0]['topicId']
    client.post(f'/api/topics/{topic_id}/bookmark', headers=headers)
    r = client.get(f'/api/topics/{topic_id}', headers=headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body['isBookmarked'] is True
    assert 'content' in body
