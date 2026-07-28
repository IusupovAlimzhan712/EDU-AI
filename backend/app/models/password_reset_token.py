from datetime import datetime, timezone

from ..extensions import db


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    token_id = db.Column('tokenId', db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    # We store a SHA-256 hash, not the raw token, so a DB leak can't be
    # used to reset passwords.
    token_hash = db.Column('tokenHash', db.String(64), nullable=False, unique=True)
    expires_at = db.Column('expiresAt', db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        'createdAt', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    student = db.relationship('Student', back_populates='reset_tokens')

    def is_valid(self) -> bool:
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return (not self.used) and datetime.now(timezone.utc) < expires

    def __repr__(self) -> str:
        return f'<PasswordResetToken student={self.student_id} used={self.used}>'
