"""
Seed essay questions for EduAI.

Generates 1 Struktur + 1 Esei question for each Form 5 chapter that has
ingested PDF pages. Validates each package before storing.

Usage:
    cd backend/
    python seed_essays.py
"""
import sys
import logging
from app import create_app
from app.extensions import db
from app.models import Chapter
from app.repositories import TopicPageRepository
from app.services import EssayService

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def has_pages(form_level: int, chapter_id: int) -> bool:
    pages = TopicPageRepository.list_for_chapter(form_level, chapter_id)
    return len([p for p in pages if p.text_content and p.text_content.strip()]) > 0


def seed(form_level: int = 5):
    app = create_app()
    with app.app_context():
        chapters = db.session.query(Chapter).filter_by(form_level=form_level).all()
        generated = 0
        failed = 0

        for chapter in chapters:
            if not has_pages(form_level, chapter.chapter_id):
                logger.info(
                    'Skipping F%d-C%d %s — no ingested pages.',
                    form_level, chapter.chapter_id, chapter.chapter_name,
                )
                continue

            for q_type, max_marks, sub_q, difficulty in [
                ('struktur', 6, '(b)', 'medium'),
                ('esei', 8, '(c)', 'hard'),
            ]:
                try:
                    eq = EssayService.generate_question_package(
                        form_level=form_level,
                        chapter_id=chapter.chapter_id,
                        question_type=q_type,
                        max_marks=max_marks,
                        sub_question=sub_q,
                        difficulty=difficulty,
                    )
                    logger.info(
                        'Generated F%d-C%d %s [%s, %dm]: Q%d — %s...',
                        form_level, chapter.chapter_id, chapter.chapter_name,
                        q_type, max_marks, eq.question_id,
                        eq.question_text[:60],
                    )
                    generated += 1
                except Exception as exc:
                    logger.error(
                        'FAILED F%d-C%d %s [%s]: %s',
                        form_level, chapter.chapter_id, chapter.chapter_name,
                        q_type, exc,
                    )
                    failed += 1

        logger.info('Done. Generated: %d, Failed: %d', generated, failed)


if __name__ == '__main__':
    form = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    seed(form)
