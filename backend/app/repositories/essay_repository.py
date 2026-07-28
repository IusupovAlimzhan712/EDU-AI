"""EssayRepository — data access for EssayQuestion and EssayAttempt."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import EssayQuestion, EssayAttempt


class EssayRepository:

    # -------------------------------------------------------------------------
    # Questions
    # -------------------------------------------------------------------------

    @staticmethod
    def list_questions(
        form_level: Optional[int] = None,
        chapter_id: Optional[int] = None,
    ) -> List[EssayQuestion]:
        q = db.session.query(EssayQuestion).options(joinedload(EssayQuestion.chapter))
        if form_level is not None:
            q = q.filter(EssayQuestion.form_level == form_level)
        if chapter_id is not None:
            q = q.filter(EssayQuestion.chapter_id == chapter_id)
        return q.order_by(EssayQuestion.form_level, EssayQuestion.chapter_id,
                          EssayQuestion.question_id).all()

    @staticmethod
    def get_question(question_id: int) -> Optional[EssayQuestion]:
        return db.session.get(EssayQuestion, question_id)

    @staticmethod
    def create_question(
        question_text: str,
        question_type: str,
        form_level: int,
        chapter_id: int,
        max_marks: int,
        marking_scheme_json: dict,
        model_answer: str,
        sub_question: Optional[str] = None,
        difficulty: str = 'medium',
    ) -> EssayQuestion:
        eq = EssayQuestion(
            question_text=question_text,
            question_type=question_type,
            form_level=form_level,
            chapter_id=chapter_id,
            sub_question=sub_question,
            max_marks=max_marks,
            difficulty=difficulty,
            marking_scheme_json=marking_scheme_json,
            model_answer=model_answer,
        )
        db.session.add(eq)
        db.session.flush()
        return eq

    @staticmethod
    def list_questions_for_chapter(
        form_level: int, chapter_id: int
    ) -> List[EssayQuestion]:
        return db.session.query(EssayQuestion).filter_by(
            form_level=form_level, chapter_id=chapter_id
        ).all()

    # -------------------------------------------------------------------------
    # Attempts
    # -------------------------------------------------------------------------

    @staticmethod
    def get_attempt(attempt_id: int) -> Optional[EssayAttempt]:
        return db.session.get(EssayAttempt, attempt_id)

    @staticmethod
    def find_draft(student_id: int, question_id: int) -> Optional[EssayAttempt]:
        return db.session.query(EssayAttempt).filter_by(
            student_id=student_id,
            question_id=question_id,
            status='draft',
        ).order_by(EssayAttempt.started_at.desc()).first()

    @staticmethod
    def create_attempt(student_id: int, question_id: int) -> EssayAttempt:
        ea = EssayAttempt(
            student_id=student_id,
            question_id=question_id,
            status='draft',
            grading_status='pending',
        )
        db.session.add(ea)
        db.session.flush()
        return ea

    @staticmethod
    def update_draft(attempt: EssayAttempt, response_text: str) -> None:
        attempt.response_text = response_text
        db.session.flush()

    @staticmethod
    def list_for_student(
        student_id: int,
        question_id: Optional[int] = None,
    ) -> List[EssayAttempt]:
        q = (
            db.session.query(EssayAttempt)
            .options(joinedload(EssayAttempt.question))
            .filter_by(student_id=student_id)
        )
        if question_id is not None:
            q = q.filter(EssayAttempt.question_id == question_id)
        return q.order_by(EssayAttempt.started_at.desc()).all()

    @staticmethod
    def get_best_attempt(student_id: int, question_id: int) -> Optional[EssayAttempt]:
        return (
            db.session.query(EssayAttempt)
            .filter_by(
                student_id=student_id,
                question_id=question_id,
                grading_status='done',
            )
            .order_by(EssayAttempt.score.desc())
            .first()
        )

    @staticmethod
    def finalize_grading(
        attempt: EssayAttempt,
        score: float,
        max_score: int,
        grading_status: str,
        is_note_form: Optional[bool],
        aras_level: Optional[int],
        matched_codes_json: Optional[list],
        feedback_json: dict,
    ) -> None:
        attempt.status = 'graded'
        attempt.grading_status = grading_status
        attempt.submitted_at = attempt.submitted_at or datetime.now(timezone.utc)
        attempt.score = score
        attempt.max_score = max_score
        attempt.is_note_form = is_note_form
        attempt.aras_level = aras_level
        attempt.matched_codes_json = matched_codes_json
        attempt.feedback_json = feedback_json
        db.session.flush()

    @staticmethod
    def set_grading_status(attempt: EssayAttempt, status: str) -> None:
        attempt.grading_status = status
        db.session.flush()
