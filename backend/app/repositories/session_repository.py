"""SessionRepository — DB access for login sessions."""
from typing import Optional

from ..extensions import db
from ..models import Session


class SessionRepository:

    @staticmethod
    def get_by_id(session_id: str) -> Optional[Session]:
        return db.session.get(Session, session_id)

    @staticmethod
    def create(session_id: str, student_id: int) -> Session:
        sess = Session(session_id=session_id, student_id=student_id, is_active=True)
        db.session.add(sess)
        db.session.flush()
        return sess

    @staticmethod
    def deactivate(session_id: str) -> None:
        sess = SessionRepository.get_by_id(session_id)
        if sess:
            sess.deactivate()
            db.session.flush()

    @staticmethod
    def deactivate_all_for_student(student_id: int) -> None:
        db.session.query(Session).filter_by(student_id=student_id).update(
            {'is_active': False}
        )

    @staticmethod
    def is_active(session_id: str) -> bool:
        sess = SessionRepository.get_by_id(session_id)
        return bool(sess and sess.is_active)
