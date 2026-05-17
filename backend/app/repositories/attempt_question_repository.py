"""AttemptQuestionRepository — per-attempt question snapshots."""
from typing import List, Optional

from ..extensions import db
from ..models import AttemptQuestion


class AttemptQuestionRepository:

    @staticmethod
    def get(attempt_question_id: int) -> Optional[AttemptQuestion]:
        return db.session.get(AttemptQuestion, attempt_question_id)

    @staticmethod
    def list_for_attempt(attempt_id: int) -> List[AttemptQuestion]:
        return db.session.query(AttemptQuestion).filter_by(
            attempt_id=attempt_id
        ).order_by(AttemptQuestion.order_index).all()

    @staticmethod
    def add(
        attempt_id: int, order_index: int,
        stem: str, options: list, correct_index: int,
        explanation: str = '', points: int = 1,
    ) -> AttemptQuestion:
        row = AttemptQuestion(
            attempt_id=attempt_id,
            order_index=order_index,
            stem=stem,
            options=options,
            correct_index=correct_index,
            explanation=explanation,
            points=points,
        )
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def count_for_attempt(attempt_id: int) -> int:
        return db.session.query(AttemptQuestion).filter_by(
            attempt_id=attempt_id
        ).count()