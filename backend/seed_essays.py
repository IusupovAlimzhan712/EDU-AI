"""
Seed essay questions for EduAI.

Generates 3 difficulty tiers × 2 question types per chapter:
  easy/medium/hard × struktur/esei → 6 questions per chapter.

Skips combinations that already exist in the database.

Usage:
    cd backend/
    python seed_essays.py [form_level]   # default: both 4 and 5
    python seed_essays.py 4
    python seed_essays.py 5
"""
import sys
import logging
from app import create_app
from app.extensions import db
from app.models import Chapter, EssayQuestion
from app.repositories import TopicPageRepository
from app.services import EssayService

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

QUESTION_COMBOS = [
    ('struktur', 6, '(b)', 'easy'),
    ('struktur', 6, '(b)', 'medium'),
    ('struktur', 6, '(b)', 'hard'),
    ('esei',     8, '(c)', 'easy'),
    ('esei',     8, '(c)', 'medium'),
    ('esei',     8, '(c)', 'hard'),
]


def has_pages(form_level: int, chapter_id: int) -> bool:
    pages = TopicPageRepository.list_for_chapter(form_level, chapter_id)
    return len([p for p in pages if p.text_content and p.text_content.strip()]) > 0


def already_exists(form_level: int, chapter_id: int, q_type: str, difficulty: str) -> bool:
    return db.session.query(EssayQuestion).filter_by(
        form_level=form_level,
        chapter_id=chapter_id,
        question_type=q_type,
        difficulty=difficulty,
    ).first() is not None


def seed(form_level: int):
    app = create_app()
    with app.app_context():
        chapters = db.session.query(Chapter).filter_by(form_level=form_level).all()
        generated = 0
        skipped = 0
        failed = 0

        for chapter in chapters:
            if not has_pages(form_level, chapter.chapter_id):
                logger.info(
                    'Skipping F%d-C%d %s — no ingested pages.',
                    form_level, chapter.chapter_id, chapter.chapter_name,
                )
                continue

            for q_type, max_marks, sub_q, difficulty in QUESTION_COMBOS:
                if already_exists(form_level, chapter.chapter_id, q_type, difficulty):
                    logger.info(
                        'Skip F%d-C%d [%s/%s] — already exists.',
                        form_level, chapter.chapter_id, q_type, difficulty,
                    )
                    skipped += 1
                    continue

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
                        'Generated F%d-C%d %s [%s/%s, %dm]: Q%d — %s...',
                        form_level, chapter.chapter_id, chapter.chapter_name,
                        q_type, difficulty, max_marks, eq.question_id,
                        eq.question_text[:60],
                    )
                    generated += 1
                except Exception as exc:
                    logger.error(
                        'FAILED F%d-C%d %s [%s/%s]: %s',
                        form_level, chapter.chapter_id, chapter.chapter_name,
                        q_type, difficulty, exc,
                    )
                    failed += 1

        logger.info(
            'Done F%d. Generated: %d, Skipped (existed): %d, Failed: %d',
            form_level, generated, skipped, failed,
        )


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if arg == '4':
        seed(4)
    elif arg == '5':
        seed(5)
    else:
        seed(4)
        seed(5)
