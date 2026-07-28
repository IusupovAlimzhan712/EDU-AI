"""
Retry the 12 failed essay question slots.

Uses a relaxed Jaccard threshold (0.72) and 5 retries per slot.
Only generates combinations that do not already exist in the database.

Usage:
    cd backend/
    python seed_essays_retry.py
"""
import logging
from app import create_app
from app.extensions import db
from app.models import EssayQuestion
from app.services import EssayService

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

MISSING = [
    (4, 2,  'struktur', 6, '(b)', 'easy'),
    (4, 3,  'struktur', 6, '(b)', 'easy'),
    (4, 4,  'struktur', 6, '(b)', 'easy'),
    (4, 5,  'struktur', 6, '(b)', 'hard'),
    (4, 5,  'esei',     8, '(c)', 'easy'),
    (4, 6,  'struktur', 6, '(b)', 'hard'),
    (4, 10, 'struktur', 6, '(b)', 'hard'),
    (5, 4,  'struktur', 6, '(b)', 'hard'),
    (5, 6,  'struktur', 6, '(b)', 'hard'),
    (5, 8,  'struktur', 6, '(b)', 'hard'),
    (5, 10, 'struktur', 6, '(b)', 'hard'),
    (5, 10, 'esei',     8, '(c)', 'easy'),
]


def already_exists(form_level, chapter_id, q_type, difficulty):
    return db.session.query(EssayQuestion).filter_by(
        form_level=form_level,
        chapter_id=chapter_id,
        question_type=q_type,
        difficulty=difficulty,
    ).first() is not None


def run():
    app = create_app()
    with app.app_context():
        generated = 0
        failed = 0
        for form_level, chapter_id, q_type, max_marks, sub_q, difficulty in MISSING:
            if already_exists(form_level, chapter_id, q_type, difficulty):
                logger.info('Skip F%d-C%d [%s/%s] — already exists.', form_level, chapter_id, q_type, difficulty)
                continue
            try:
                eq = EssayService.generate_question_package(
                    form_level=form_level,
                    chapter_id=chapter_id,
                    question_type=q_type,
                    max_marks=max_marks,
                    sub_question=sub_q,
                    difficulty=difficulty,
                    max_retries=5,
                )
                logger.info(
                    'Generated F%d-C%d [%s/%s]: Q%d — %s...',
                    form_level, chapter_id, q_type, difficulty,
                    eq.question_id, eq.question_text[:60],
                )
                generated += 1
            except Exception as exc:
                logger.error('FAILED F%d-C%d [%s/%s]: %s', form_level, chapter_id, q_type, difficulty, exc)
                failed += 1

        logger.info('Done. Generated: %d, Failed: %d', generated, failed)


if __name__ == '__main__':
    run()
