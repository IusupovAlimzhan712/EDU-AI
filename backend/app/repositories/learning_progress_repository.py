"""LearningProgressRepository — DB access for LearningProgress + junction tables."""
from datetime import date, timedelta
from typing import List, Optional

from ..extensions import db
from ..models import LearningProgress, CompletedTopic, BookmarkedTopic, Topic


class LearningProgressRepository:

    @staticmethod
    def get_by_student_id(student_id: int) -> Optional[LearningProgress]:
        return db.session.query(LearningProgress).filter_by(
            student_id=student_id
        ).first()

    @staticmethod
    def create_for_student(student_id: int) -> LearningProgress:
        progress = LearningProgress(student_id=student_id)
        db.session.add(progress)
        db.session.flush()
        return progress

    # ---- Completed topics ----

    @staticmethod
    def get_completed_topic(progress_id: int, topic_id: int) -> Optional[CompletedTopic]:
        return db.session.get(CompletedTopic, (progress_id, topic_id))

    @staticmethod
    def list_completed_topic_ids(progress_id: int) -> List[int]:
        rows = db.session.query(CompletedTopic.topic_id).filter_by(
            progress_id=progress_id
        ).all()
        return [r[0] for r in rows]

    @staticmethod
    def mark_completed(progress_id: int, topic_id: int) -> CompletedTopic:
        existing = LearningProgressRepository.get_completed_topic(progress_id, topic_id)
        if existing:
            return existing
        row = CompletedTopic(progress_id=progress_id, topic_id=topic_id)
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def count_completed_in_chapter(progress_id: int, form_level: int, chapter_id: int) -> int:
        return (
            db.session.query(db.func.count(CompletedTopic.topic_id))
            .join(Topic, CompletedTopic.topic_id == Topic.topic_id)
            .filter(
                CompletedTopic.progress_id == progress_id,
                Topic.form_level == form_level,
                Topic.chapter_id == chapter_id,
            )
            .scalar() or 0
        )

    @staticmethod
    def unmark_completed(progress_id: int, topic_id: int) -> bool:
        existing = LearningProgressRepository.get_completed_topic(progress_id, topic_id)
        if not existing:
            return False
        db.session.delete(existing)
        db.session.flush()
        return True

    # ---- Bookmarks ----

    @staticmethod
    def get_bookmark(progress_id: int, topic_id: int) -> Optional[BookmarkedTopic]:
        return db.session.get(BookmarkedTopic, (progress_id, topic_id))

    @staticmethod
    def list_bookmarked_topic_ids(progress_id: int) -> List[int]:
        rows = db.session.query(BookmarkedTopic.topic_id).filter_by(
            progress_id=progress_id
        ).all()
        return [r[0] for r in rows]

    @staticmethod
    def list_bookmarks(progress_id: int) -> List[BookmarkedTopic]:
        return db.session.query(BookmarkedTopic).filter_by(
            progress_id=progress_id
        ).order_by(BookmarkedTopic.bookmarked_at.desc()).all()

    @staticmethod
    def add_bookmark(progress_id: int, topic_id: int) -> BookmarkedTopic:
        existing = LearningProgressRepository.get_bookmark(progress_id, topic_id)
        if existing:
            return existing
        row = BookmarkedTopic(progress_id=progress_id, topic_id=topic_id)
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def remove_bookmark(progress_id: int, topic_id: int) -> bool:
        existing = LearningProgressRepository.get_bookmark(progress_id, topic_id)
        if not existing:
            return False
        db.session.delete(existing)
        db.session.flush()
        return True

    # ---- Streak ----

    @staticmethod
    def update_streak(progress: LearningProgress) -> None:
        """Increment streak if today is a new study day; reset if streak was broken.

        Called every time a topic is marked complete. Idempotent within one day:
        multiple completions on the same day don't change the streak count beyond 1.
        """
        today = date.today()
        last = progress.last_study_date

        if last is None:
            progress.current_streak = 1
        elif last == today:
            return  # already studied today, no change needed
        elif last == today - timedelta(days=1):
            progress.current_streak = (progress.current_streak or 0) + 1
        else:
            progress.current_streak = 1  # gap in study days — reset streak

        progress.last_study_date = today
        db.session.flush()
