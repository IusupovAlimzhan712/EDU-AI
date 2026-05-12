"""TopicPageRepository — data access for per-page topic text."""
from typing import List, Optional

from ..extensions import db
from ..models import TopicPage


class TopicPageRepository:

    @staticmethod
    def get(topic_id: int, page_number: int) -> Optional[TopicPage]:
        return db.session.query(TopicPage).filter_by(
            topic_id=topic_id, page_number=page_number
        ).first()

    @staticmethod
    def list_for_topic(topic_id: int) -> List[TopicPage]:
        return db.session.query(TopicPage).filter_by(
            topic_id=topic_id
        ).order_by(TopicPage.page_number).all()

    @staticmethod
    def list_for_chapter(form_level: int, chapter_id: int) -> List[TopicPage]:
        """Used by Phase 3 quiz generation — all pages across a chapter."""
        from ..models import Topic
        return (
            db.session.query(TopicPage)
            .join(Topic, TopicPage.topic_id == Topic.topic_id)
            .filter(Topic.form_level == form_level, Topic.chapter_id == chapter_id)
            .order_by(Topic.topic_id, TopicPage.page_number)
            .all()
        )

    @staticmethod
    def delete_all_for_topic(topic_id: int) -> int:
        """Used by the ingest script when re-importing a topic."""
        count = db.session.query(TopicPage).filter_by(topic_id=topic_id).delete()
        db.session.flush()
        return count

    @staticmethod
    def bulk_insert(rows: list) -> None:
        """rows = list of dicts: {topic_id, page_number, text_content, word_count}"""
        if not rows:
            return
        objs = [TopicPage(**r) for r in rows]
        db.session.bulk_save_objects(objs)
        db.session.flush()