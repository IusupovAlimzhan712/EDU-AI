"""AttemptQuestionRepository — per-attempt question snapshots."""
import random
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
        # Shuffle options so the correct answer is not always at the LLM's
        # preferred position (almost always index 0 due to prompt anchoring).
        # shuffled_order[i] is the original index of the element now at position i.
        shuffled_order = list(range(len(options)))
        random.shuffle(shuffled_order)
        shuffled_options = [options[i] for i in shuffled_order]
        # Find where the original correct answer landed after shuffle.
        new_correct_index = shuffled_order.index(correct_index)

        row = AttemptQuestion(
            attempt_id=attempt_id,
            order_index=order_index,
            stem=stem,
            options=shuffled_options,
            correct_index=new_correct_index,
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