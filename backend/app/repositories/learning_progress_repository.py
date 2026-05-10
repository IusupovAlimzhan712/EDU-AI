"""LearningProgressRepository — DB access for LearningProgress + junction tables."""
from typing import List, Optional

from ..extensions import db
from ..models import LearningProgress, CompletedTopic, BookmarkedTopic


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
