"""TopicRepository — DB access for Topic rows."""
from typing import List, Optional

from ..extensions import db
from ..models import Topic


class TopicRepository:

    @staticmethod
    def get_by_id(topic_id: int) -> Optional[Topic]:
        return db.session.get(Topic, topic_id)

    @staticmethod
    def list_filtered(
        form_level: Optional[int] = None,
        chapter_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Topic]:
        """List topics with optional filters.

        - `form_level`: 4 or 5
        - `chapter_id`: requires form_level to be unambiguous
        - `search`: case-insensitive substring on topic_name
        """
        q = db.session.query(Topic)
        if form_level is not None:
            q = q.filter(Topic.form_level == form_level)
        if chapter_id is not None:
            q = q.filter(Topic.chapter_id == chapter_id)
        if search:
            like = f"%{search.lower()}%"
            q = q.filter(db.func.lower(Topic.topic_name).like(like))
        return q.order_by(
            Topic.form_level, Topic.chapter_id, Topic.topic_id
        ).all()

    @staticmethod
    def list_by_ids(topic_ids: List[int]) -> List[Topic]:
        if not topic_ids:
            return []
        return db.session.query(Topic).filter(Topic.topic_id.in_(topic_ids)).all()
