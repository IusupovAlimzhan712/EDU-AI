"""PasswordResetRepository — DB access for password-reset tokens."""
from datetime import datetime, timedelta
from typing import Optional

from ..extensions import db
from ..models import PasswordResetToken


class PasswordResetRepository:

    @staticmethod
    def create(student_id: int, token_hash: str, expires_in_seconds: int) -> PasswordResetToken:
        token = PasswordResetToken(
            student_id=student_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in_seconds),
            used=False,
        )
        db.session.add(token)
        db.session.flush()
        return token

    @staticmethod
    def get_by_hash(token_hash: str) -> Optional[PasswordResetToken]:
        return db.session.query(PasswordResetToken).filter_by(
            token_hash=token_hash
        ).first()

    @staticmethod
    def mark_used(token: PasswordResetToken) -> None:
        token.used = True
        db.session.flush()

    @staticmethod
    def invalidate_all_for_student(student_id: int) -> None:
        """Used after a successful reset, to invalidate any other outstanding tokens."""
        db.session.query(PasswordResetToken).filter_by(
            student_id=student_id, used=False
        ).update({'used': True})
