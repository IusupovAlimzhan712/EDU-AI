"""QuizRepository — quiz templates only (questions now live per-attempt)."""
from typing import List, Optional

from ..extensions import db
from ..models import Quiz


class QuizRepository:

    @staticmethod
    def get(quiz_id: int) -> Optional[Quiz]:
        return db.session.get(Quiz, quiz_id)

    @staticmethod
    def list_all(form_level: Optional[int] = None) -> List[Quiz]:
        q = db.session.query(Quiz)
        if form_level is not None:
            q = q.filter(Quiz.form_level == form_level)
        return q.order_by(
            Quiz.form_level,
            Quiz.chapter_id.is_(None).desc(),
            Quiz.chapter_id,
        ).all()

    @staticmethod
    def find_by_scope(
        form_level: int, chapter_id: Optional[int], scope: str
    ) -> Optional[Quiz]:
        return db.session.query(Quiz).filter_by(
            form_level=form_level, chapter_id=chapter_id, scope=scope
        ).first()

    @staticmethod
    def upsert(
        form_level: int,
        chapter_id: Optional[int],
        scope: str,
        title: str,
        default_question_count: int = 10,
    ) -> Quiz:
        quiz = QuizRepository.find_by_scope(form_level, chapter_id, scope)
        if quiz:
            quiz.title = title
            quiz.default_question_count = default_question_count
        else:
            quiz = Quiz(
                form_level=form_level,
                chapter_id=chapter_id,
                scope=scope,
                title=title,
                default_question_count=default_question_count,
                source='ai',
            )
            db.session.add(quiz)
        db.session.flush()
        return quiz