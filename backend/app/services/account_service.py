"""
AccountService — implementation of the `AccountManager` Control class
described in Table 4.28 / Section 6.3.2 of the FYP1 report.

Responsibilities:
  - Register a student, validating uniqueness of email (UC 4.3.1 + 4.3.3)
  - Authenticate logins (UC 4.3.2)
  - Manage login sessions: create on login, deactivate on logout
    (UC 4.3.5, 4.3.6)
  - Reset password via secure single-use token (UC 4.3.4)
  - Update profile, change password, delete account
  - Create the one-to-one LearningProgress row on registration
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple

from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
)

from ..extensions import bcrypt
from ..models import Student
from ..repositories import (
    StudentRepository,
    SessionRepository,
    LearningProgressRepository,
    PasswordResetRepository,
)
from ..utils.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    BadRequestError,
)
from ..utils.validators import (
    validate_email_address,
    validate_password,
    validate_full_name,
    validate_form_level,
)


class AccountService:

    # =====================================================================
    # Registration
    # =====================================================================

    @staticmethod
    def register(
        email: str,
        password: str,
        full_name: str,
        form_level,
    ) -> Tuple[Student, dict]:
        """Register a new student account.

        Returns (student, tokens) where tokens is {accessToken, refreshToken}.
        """
        # --- Validate inputs ---
        email = validate_email_address(email)
        validate_password(password)
        full_name = validate_full_name(full_name)
        form_level = validate_form_level(form_level)

        # --- Duplicate check (UC 4.3.3) ---
        if StudentRepository.email_exists(email):
            raise ConflictError('An account with this email already exists.')

        # --- Hash password ---
        rounds = current_app.config.get('BCRYPT_LOG_ROUNDS', 12)
        password_hash = bcrypt.generate_password_hash(
            password, rounds=rounds
        ).decode('utf-8')

        # --- Create student + learning_progress in one transaction ---
        try:
            student = StudentRepository.create(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                form_level=form_level,
            )
            LearningProgressRepository.create_for_student(student.student_id)
            StudentRepository.commit()
        except Exception:
            StudentRepository.rollback()
            raise

        # --- Issue tokens + create Session row ---
        tokens = AccountService._issue_tokens(student)
        return student, tokens

    # =====================================================================
    # Authentication
    # =====================================================================

    @staticmethod
    def login(email: str, password: str) -> Tuple[Student, dict]:
        """Authenticate an email + password pair (UC 4.3.2).

        Returns (student, tokens). Raises UnauthorizedError on bad creds.
        """
        if not email or not password:
            raise UnauthorizedError('Email and password are required.')

        student = StudentRepository.get_by_email(email.strip())
        # Generic message — don't leak whether the email exists.
        if not student or not bcrypt.check_password_hash(student.password_hash, password):
            raise UnauthorizedError('Invalid email or password.')

        tokens = AccountService._issue_tokens(student)
        StudentRepository.commit()
        return student, tokens

    @staticmethod
    def logout(jti: str) -> None:
        """Deactivate the current session (UC 4.3.6)."""
        if not jti:
            return
        SessionRepository.deactivate(jti)
        StudentRepository.commit()

    @staticmethod
    def refresh_token(student_id: int) -> dict:
        """Issue a new access token from a valid refresh token."""
        student = StudentRepository.get_by_id(student_id)
        if not student:
            raise UnauthorizedError('Account no longer exists.')

        access_token = create_access_token(identity=str(student.student_id))
        # Register the new access token as an active Session
        from flask_jwt_extended import decode_token
        decoded = decode_token(access_token)
        SessionRepository.create(decoded['jti'], student.student_id)
        StudentRepository.commit()
        return {'accessToken': access_token}

    # =====================================================================
    # Profile management
    # =====================================================================

    @staticmethod
    def get_profile(student_id: int) -> Student:
        student = StudentRepository.get_by_id(student_id)
        if not student:
            raise NotFoundError('Student not found.')
        return student

    @staticmethod
    def update_profile(
        student_id: int,
        full_name: Optional[str] = None,
        form_level=None,
    ) -> Student:
        student = AccountService.get_profile(student_id)
        if full_name is not None:
            student.full_name = validate_full_name(full_name)
        if form_level is not None:
            student.form_level = validate_form_level(form_level)
        StudentRepository.commit()
        return student

    @staticmethod
    def change_password(
        student_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        student = AccountService.get_profile(student_id)
        if not current_password or not bcrypt.check_password_hash(
            student.password_hash, current_password
        ):
            raise UnauthorizedError('Current password is incorrect.')
        validate_password(new_password)
        rounds = current_app.config.get('BCRYPT_LOG_ROUNDS', 12)
        student.password_hash = bcrypt.generate_password_hash(
            new_password, rounds=rounds
        ).decode('utf-8')
        # Invalidate all existing sessions so the user has to log in fresh.
        SessionRepository.deactivate_all_for_student(student_id)
        StudentRepository.commit()

    @staticmethod
    def delete_account(student_id: int) -> None:
        student = AccountService.get_profile(student_id)
        StudentRepository.delete(student)
        StudentRepository.commit()

    # =====================================================================
    # Password reset (UC 4.3.4)
    # =====================================================================

    @staticmethod
    def request_password_reset(email: str) -> Optional[str]:
        """Generate a single-use reset token for `email`.

        Always returns the same shape regardless of whether the email
        exists (prevents account enumeration). In dev mode (per config),
        the raw token is returned so the frontend can show / open it
        without an SMTP server.
        """
        try:
            email = validate_email_address(email)
        except ValidationError:
            return None  # silently accept

        student = StudentRepository.get_by_email(email)
        if not student:
            return None  # don't reveal that the email is missing

        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_in = current_app.config['PASSWORD_RESET_TOKEN_EXPIRES']

        PasswordResetRepository.create(student.student_id, token_hash, expires_in)
        StudentRepository.commit()

        # TODO(Phase 1 — optional): send email via SMTP when configured.
        # For dev convenience we just return the raw token.
        if current_app.config.get('DEV_RETURN_RESET_TOKEN'):
            return raw_token
        return None

    @staticmethod
    def reset_password(token: str, new_password: str) -> None:
        """Consume a reset token and set the new password."""
        if not token:
            raise BadRequestError('Reset token is required.')
        validate_password(new_password)

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        record = PasswordResetRepository.get_by_hash(token_hash)
        if not record or not record.is_valid():
            raise UnauthorizedError('Invalid or expired reset token.')

        student = StudentRepository.get_by_id(record.student_id)
        if not student:
            raise NotFoundError('Account no longer exists.')

        rounds = current_app.config.get('BCRYPT_LOG_ROUNDS', 12)
        student.password_hash = bcrypt.generate_password_hash(
            new_password, rounds=rounds
        ).decode('utf-8')

        PasswordResetRepository.mark_used(record)
        PasswordResetRepository.invalidate_all_for_student(student.student_id)
        SessionRepository.deactivate_all_for_student(student.student_id)
        StudentRepository.commit()

    # =====================================================================
    # Session validity check (used by routes after JWT validates)
    # =====================================================================

    @staticmethod
    def assert_session_active(jti: str) -> None:
        """Raise if the JWT's session has been deactivated (logged out)."""
        if not SessionRepository.is_active(jti):
            raise UnauthorizedError('Session has been terminated. Please log in again.')

    # =====================================================================
    # Internal helpers
    # =====================================================================

    @staticmethod
    def _issue_tokens(student: Student) -> dict:
        """Create access + refresh tokens and persist a Session row.

        The Session row's ID is the JWT's `jti`, so logout can target the
        specific token.
        """
        access_token = create_access_token(identity=str(student.student_id))
        refresh_token = create_refresh_token(identity=str(student.student_id))

        from flask_jwt_extended import decode_token
        decoded = decode_token(access_token)
        SessionRepository.create(decoded['jti'], student.student_id)

        return {
            'accessToken': access_token,
            'refreshToken': refresh_token,
        }
