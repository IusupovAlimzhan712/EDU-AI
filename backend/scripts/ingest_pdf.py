"""
Extract text from each Topic's PDF and populate the topic_page table.

Usage:
    cd backend

    # Ingest ALL topics that have a pdf_path set:
    python -m scripts.ingest_pdf

    # Ingest a single topic by id:
    python -m scripts.ingest_pdf --topic 3

    # Force re-ingest even if pages already exist:
    python -m scripts.ingest_pdf --force

Notes:
  - Assumes PDFs have selectable text. Scanned/image-only PDFs will
    yield empty page rows; the script will warn but not fail.
  - Safe to re-run: existing topic_page rows for a topic are deleted
    before re-inserting.
"""
import argparse
import os
import sys

from pypdf import PdfReader

from app import create_app
from app.extensions import db
from app.models import Topic
from app.repositories import TopicPageRepository


def find_pdf_root(app) -> str:
    backend_root = os.path.dirname(app.root_path)
    return os.path.join(backend_root, 'static', 'pdfs')


def ingest_topic(topic: Topic, pdf_root: str, force: bool) -> bool:
    """Return True if pages were ingested, False if skipped."""
    if not topic.pdf_path:
        print(f'  ⚠ Topic {topic.topic_id} ({topic.topic_name}): no pdf_path set, skipping.')
        return False

    abs_path = os.path.join(pdf_root, topic.pdf_path)
    if not os.path.isfile(abs_path):
        print(f'  ⚠ Topic {topic.topic_id} ({topic.topic_name}): file not found at {abs_path}, skipping.')
        return False

    existing = topic.pages
    if existing and not force:
        print(f'  ⊙ Topic {topic.topic_id} ({topic.topic_name}): already has '
              f'{len(existing)} pages, skipping (use --force to re-ingest).')
        return False

    try:
        reader = PdfReader(abs_path)
    except Exception as exc:
        print(f'  ✗ Topic {topic.topic_id}: failed to read PDF: {exc}')
        return False

    # Clear existing pages if any
    if existing:
        TopicPageRepository.delete_all_for_topic(topic.topic_id)

    rows = []
    empty_pages = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ''
        except Exception:
            text = ''
        text = text.strip()
        if not text:
            empty_pages += 1
        rows.append({
            'topic_id': topic.topic_id,
            'page_number': i,
            'text_content': text,
            'word_count': len(text.split()),
        })

    TopicPageRepository.bulk_insert(rows)
    topic.total_pages = len(rows)
    db.session.commit()

    status = f'  ✓ Topic {topic.topic_id} ({topic.topic_name}): {len(rows)} pages ingested'
    if empty_pages:
        status += f' (warning: {empty_pages} empty — likely scanned/image-only PDF)'
    print(status)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=int, help='Ingest only this topicId')
    parser.add_argument('--force', action='store_true',
                        help='Re-ingest topics that already have pages')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        pdf_root = find_pdf_root(app)
        print(f'PDF root: {pdf_root}')

        q = db.session.query(Topic)
        if args.topic:
            q = q.filter(Topic.topic_id == args.topic)
        topics = q.all()
        if not topics:
            print('No topics matched.')
            sys.exit(0)

        ingested = 0
        for t in topics:
            if ingest_topic(t, pdf_root, args.force):
                ingested += 1
        print()
        print(f'Done. {ingested}/{len(topics)} topics ingested.')


if __name__ == '__main__':
    main()