"""Seed the 22 quiz templates (no questions — those are AI-generated per attempt)."""
from app import create_app
from app.extensions import db
from app.models import Chapter
from app.repositories import QuizRepository


def seed_quiz_placeholders():
    chapters = db.session.query(Chapter).order_by(
        Chapter.form_level, Chapter.chapter_id
    ).all()
    if not chapters:
        print('✗ No chapters found. Run `python -m scripts.seed` first.')
        return

    created = 0
    for c in chapters:
        QuizRepository.upsert(
            form_level=c.form_level,
            chapter_id=c.chapter_id,
            scope='bab',
            title=f'Quiz: Bab {c.chapter_id} — {c.chapter_name} (Form {c.form_level})',
            default_question_count=10,
        )
        created += 1


    db.session.commit()
    print(f'✓ Ensured {created} per-Bab quiz templates.')


def main():
    app = create_app()
    with app.app_context():
        seed_quiz_placeholders()


if __name__ == '__main__':
    main()