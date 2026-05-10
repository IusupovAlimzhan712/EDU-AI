"""
Shared pytest fixtures.

We use the TestingConfig which runs against an in-memory SQLite DB so the
tests don't need a running MySQL server. Bcrypt rounds are turned down to
4 (vs 12 in dev) so registration tests stay fast.
"""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture(scope='function')
def app():
    """A fresh Flask app + DB schema per test."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()
