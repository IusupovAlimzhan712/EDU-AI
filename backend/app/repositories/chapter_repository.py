"""ChapterRepository — DB access for KSSM Sejarah chapters."""
from typing import List, Optional

from ..extensions import db
from ..models import Chapter


class ChapterRepository:

    @staticmethod
    def list_all() -> List[Chapter]:
        return db.session.query(Chapter).order_by(
            Chapter.form_level, Chapter.chapter_id
        ).all()

    @staticmethod
    def list_by_form_level(form_level: int) -> List[Chapter]:
        return db.session.query(Chapter).filter_by(
            form_level=form_level
        ).order_by(Chapter.chapter_id).all()

    @staticmethod
    def get(form_level: int, chapter_id: int) -> Optional[Chapter]:
        return db.session.get(Chapter, (form_level, chapter_id))

    @staticmethod
    def exists(form_level: int, chapter_id: int) -> bool:
        return ChapterRepository.get(form_level, chapter_id) is not None
