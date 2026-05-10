"""
Input-validation helpers used by routes and services.

Keeping validation here (rather than in models) follows the Single
Responsibility Principle from Section 5.3.1: models hold state, services
hold business logic, and these helpers hold pure validation logic.
"""
import re
from email_validator import validate_email, EmailNotValidError

from .errors import ValidationError


PASSWORD_MIN_LENGTH = 8


def validate_email_address(email: str) -> str:
    """Normalize and validate an email. Returns the normalized form.

    Raises:
        ValidationError: if the email is missing or invalid.
    """
    if not email or not isinstance(email, str):
        raise ValidationError(errors={'email': 'Email is required'})
    try:
        result = validate_email(email.strip(), check_deliverability=False)
        return result.normalized
    except EmailNotValidError as exc:
        raise ValidationError(errors={'email': str(exc)})


def validate_password(password: str) -> None:
    """Check password meets project rules.

    Rules (matching the frontend Register form):
      - at least 8 characters
      - at least one uppercase letter
      - at least one lowercase letter
      - at least one digit

    Raises:
        ValidationError: if any rule fails.
    """
    if not password or not isinstance(password, str):
        raise ValidationError(errors={'password': 'Password is required'})
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(errors={
            'password': f'Password must be at least {PASSWORD_MIN_LENGTH} characters'
        })
    if not re.search(r'[A-Z]', password):
        raise ValidationError(errors={
            'password': 'Password must contain at least one uppercase letter'
        })
    if not re.search(r'[a-z]', password):
        raise ValidationError(errors={
            'password': 'Password must contain at least one lowercase letter'
        })
    if not re.search(r'\d', password):
        raise ValidationError(errors={
            'password': 'Password must contain at least one number'
        })


def validate_form_level(form_level) -> int:
    """KSSM Sejarah has only Form 4 and Form 5."""
    try:
        level = int(form_level)
    except (TypeError, ValueError):
        raise ValidationError(errors={'formLevel': 'Form level must be 4 or 5'})
    if level not in (4, 5):
        raise ValidationError(errors={'formLevel': 'Form level must be 4 or 5'})
    return level


def validate_full_name(name: str) -> str:
    """Strip + check non-empty + reasonable length."""
    if not name or not isinstance(name, str):
        raise ValidationError(errors={'fullName': 'Full name is required'})
    cleaned = name.strip()
    if len(cleaned) < 2:
        raise ValidationError(errors={'fullName': 'Full name is too short'})
    if len(cleaned) > 100:
        raise ValidationError(errors={'fullName': 'Full name is too long'})
    return cleaned
