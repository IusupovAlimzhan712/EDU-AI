"""
Custom exception classes for the API.

Services raise these instead of returning ad-hoc error tuples; the global
error handler in `app/__init__.py` converts them to JSON responses.
"""


class APIError(Exception):
    """Base class for all custom API errors."""
    status_code = 500
    error_name = 'Internal Server Error'

    def __init__(self, message=None, payload=None):
        super().__init__()
        self.message = message or self.error_name
        self.payload = payload or {}

    def to_dict(self):
        result = {
            'error': self.error_name,
            'message': self.message,
        }
        if self.payload:
            result.update(self.payload)
        return result


class BadRequestError(APIError):
    status_code = 400
    error_name = 'Bad Request'


class ValidationError(APIError):
    status_code = 422
    error_name = 'Validation Error'

    def __init__(self, message='Validation failed', errors=None):
        super().__init__(message=message, payload={'errors': errors or {}})


class UnauthorizedError(APIError):
    status_code = 401
    error_name = 'Unauthorized'


class ForbiddenError(APIError):
    status_code = 403
    error_name = 'Forbidden'


class NotFoundError(APIError):
    status_code = 404
    error_name = 'Not Found'


class ConflictError(APIError):
    """For e.g. duplicate-registration cases (UC 4.3.3)."""
    status_code = 409
    error_name = 'Conflict'


class TooManyRequestsError(APIError):
    """Account temporarily locked after repeated failed login attempts (UC-F1.2 E1)."""
    status_code = 429
    error_name = 'Too Many Requests'
