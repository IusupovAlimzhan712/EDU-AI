"""Tests for the Study Streak feature on LearningProgress."""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Chapter, Topic, LearningProgress
from app.repositories import LearningProgressRepository, StudentRepository


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _register(client, email='streak_user@example.com'):
    r = client.post('/api/auth/register', json={
        'email': email,
        'password': 'SecurePass1',
        'fullName': 'Streak User',
        'formLevel': 4,
    })
    data = r.get_json()
    return data['accessToken'], data['student']['studentId']


def _auth(client, email='streak_user@example.com'):
    token, sid = _register(client, email)
    return {'Authorization': f'Bearer {token}'}, sid


def _seed_topic(app):
    with app.app_context():
        db.session.add(Chapter(form_level=4, chapter_id=1, chapter_name='Bab 1'))
        db.session.commit()
        db.session.add(Topic(form_level=4, chapter_id=1, topic_name='Topik A'))
        db.session.commit()
        return db.session.query(Topic).first().topic_id


# ---------------------------------------------------------------------------
# unit tests — repository logic
# ---------------------------------------------------------------------------

def test_streak_starts_at_one_on_first_completion(app, client):
    headers, sid = _auth(client)
    topic_id = _seed_topic(app)

    r = client.post(f'/api/topics/{topic_id}/complete', headers=headers)
    assert r.status_code in (200, 201)

    r2 = client.get('/api/me/progress', headers=headers)
    assert r2.status_code == 200
    data = r2.get_json()
    assert data['currentStreak'] == 1
    assert data['lastStudyDate'] is not None


def test_streak_idempotent_same_day(app, client):
    """Completing a second topic on the same day should not increment streak."""
    headers, sid = _auth(client)
    with app.app_context():
        db.session.add(Chapter(form_level=4, chapter_id=1, chapter_name='Bab 1'))
        db.session.commit()
        db.session.add_all([
            Topic(form_level=4, chapter_id=1, topic_name='Topik A'),
            Topic(form_level=4, chapter_id=1, topic_name='Topik B'),
        ])
        db.session.commit()
        topics = db.session.query(Topic).all()
        tid1, tid2 = topics[0].topic_id, topics[1].topic_id

    client.post(f'/api/topics/{tid1}/complete', headers=headers)
    client.post(f'/api/topics/{tid2}/complete', headers=headers)

    r = client.get('/api/me/progress', headers=headers)
    assert r.get_json()['currentStreak'] == 1


def test_streak_increments_consecutive_day(app, client):
    """If lastStudyDate is yesterday, streak should increment by 1."""
    headers, sid = _auth(client)
    topic_id = _seed_topic(app)

    with app.app_context():
        progress = LearningProgressRepository.get_by_student_id(sid)
        progress.last_study_date = date.today() - timedelta(days=1)
        progress.current_streak = 3
        StudentRepository.commit()

    r = client.post(f'/api/topics/{topic_id}/complete', headers=headers)
    assert r.status_code in (200, 201)

    r2 = client.get('/api/me/progress', headers=headers)
    assert r2.get_json()['currentStreak'] == 4


def test_streak_resets_after_gap(app, client):
    """If lastStudyDate is 2+ days ago, streak should reset to 1."""
    headers, sid = _auth(client)
    topic_id = _seed_topic(app)

    with app.app_context():
        progress = LearningProgressRepository.get_by_student_id(sid)
        progress.last_study_date = date.today() - timedelta(days=3)
        progress.current_streak = 10
        StudentRepository.commit()

    client.post(f'/api/topics/{topic_id}/complete', headers=headers)

    r = client.get('/api/me/progress', headers=headers)
    assert r.get_json()['currentStreak'] == 1


def test_streak_in_progress_overview(app, client):
    """Progress overview endpoint must return currentStreak and lastStudyDate."""
    headers, _ = _auth(client)
    r = client.get('/api/me/progress', headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert 'currentStreak' in data
    assert 'lastStudyDate' in data
    assert data['currentStreak'] == 0
    assert data['lastStudyDate'] is None
