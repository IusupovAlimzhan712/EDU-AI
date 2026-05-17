"""QuizAttemptRepository — attempts + answers (FK now to attempt_question)."""
from datetime import datetime
from typing import List, Optional

from ..extensions import db
from ..models import QuizAttempt, AttemptAnswer


class QuizAttemptRepository:

    @staticmethod
    def get(attempt_id: int) -> Optional[QuizAttempt]:
        return db.session.get(QuizAttempt, attempt_id)

    @staticmethod
    def create(
        student_id: int, quiz_id: int,
        target_question_count: int = 10,
    ) -> QuizAttempt:
        att = QuizAttempt(
            student_id=student_id,
            quiz_id=quiz_id,
            status='in_progress',
            generation_status='pending',
            target_question_count=target_question_count,
        )
        db.session.add(att)
        db.session.flush()
        return att

    @staticmethod
    def find_in_progress(student_id: int, quiz_id: int) -> Optional[QuizAttempt]:
        return db.session.query(QuizAttempt).filter_by(
            student_id=student_id, quiz_id=quiz_id, status='in_progress'
        ).order_by(QuizAttempt.started_at.desc()).first()

    @staticmethod
    def list_for_student(
        student_id: int, quiz_id: Optional[int] = None
    ) -> List[QuizAttempt]:
        q = db.session.query(QuizAttempt).filter_by(student_id=student_id)
        if quiz_id is not None:
            q = q.filter(QuizAttempt.quiz_id == quiz_id)
        return q.order_by(QuizAttempt.started_at.desc()).all()

    @staticmethod
    def set_generation_status(attempt: QuizAttempt, status: str) -> None:
        attempt.generation_status = status
        db.session.flush()

    @staticmethod
    def finalize(
        attempt: QuizAttempt, score: int, max_score: int,
        correct_count: int, total_questions: int,
    ) -> None:
        attempt.status = 'submitted'
        attempt.submitted_at = datetime.utcnow()
        attempt.score = score
        attempt.max_score = max_score
        attempt.correct_count = correct_count
        attempt.total_questions = total_questions
        db.session.flush()

    @staticmethod
    def get_answer(attempt_id: int, attempt_question_id: int) -> Optional[AttemptAnswer]:
        return db.session.get(AttemptAnswer, (attempt_id, attempt_question_id))

    @staticmethod
    def upsert_answer(
        attempt_id: int, attempt_question_id: int, selected_index: Optional[int]
    ) -> AttemptAnswer:
        ans = QuizAttemptRepository.get_answer(attempt_id, attempt_question_id)
        if ans:
            ans.selected_index = selected_index
        else:
            ans = AttemptAnswer(
                attempt_id=attempt_id,
                attempt_question_id=attempt_question_id,
                selected_index=selected_index,
            )
            db.session.add(ans)
        db.session.flush()
        return ans

    @staticmethod
    def list_answers(attempt_id: int) -> List[AttemptAnswer]:
        return db.session.query(AttemptAnswer).filter_by(
            attempt_id=attempt_id
        ).all()