"""
Authentication decorators.

`@auth_required` chains JWT validation with our session-active check, so
a logged-out JWT (still cryptographically valid but explicitly revoked)
is rejected.
"""
from functools import wraps

from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from ..services import AccountService


def auth_required(fn):
    """Combination of `@jwt_required()` + active-session check."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        jti = get_jwt().get('jti')
        AccountService.assert_session_active(jti)
        return fn(*args, **kwargs)
    return wrapper


def current_student_id() -> int:
    """Helper to pull the student id out of the JWT identity."""
    return int(get_jwt_identity())
