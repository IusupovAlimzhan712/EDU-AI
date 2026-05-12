"""
Seed KSSM Sejarah Form 4 + Form 5 chapters and topics.

Real-syllabus version: 10 Babs per form, one PDF per Bab. Each Bab is
modeled as a single "topic" pointing at the corresponding PDF file in
backend/static/pdfs/Form{4,5}/Bab{N}/Bab_{N}_*.pdf.

Usage:
    cd backend
    python -m scripts.seed
"""
from app import create_app
from app.extensions import db
from app.models import Chapter, Topic, TopicPage


# ---------- Chapter definitions (matches the actual KSSM Sejarah) ----------

FORM4_CHAPTERS = [
    (1,  'Warisan Negara Bangsa'),
    (2,  'Kebangkitan Nasionalisme'),
    (3,  'Konflik Dunia dan Pendudukan Jepun di Negara Kita'),
    (4,  'Era Pentadbiran Britania di Negara Kita'),
    (5,  'Persekutuan Tanah Melayu 1948'),
    (6,  'Ancaman Komunis dan Perisytiharan Darurat'),
    (7,  'Usaha ke Arah Kemerdekaan'),
    (8,  'Pilihan Raya'),
    (9,  'Perlembagaan Persekutuan Tanah Melayu 1957'),
    (10, 'Pemasyhuran Kemerdekaan'),
]

FORM5_CHAPTERS = [
    (1,  'Kedaulatan Negara'),
    (2,  'Perlembagaan Persekutuan'),
    (3,  'Raja Berperlembagaan dan Demokrasi Berparlimen'),
    (4,  'Sistem Persekutuan'),
    (5,  'Pembentukan Malaysia'),
    (6,  'Cabaran Selepas Pembentukan Malaysia'),
    (7,  'Membina Kesejahteraan Negara'),
    (8,  'Membina Kemakmuran Negara'),
    (9,  'Dasar Luar Malaysia'),
    (10, 'Kecemerlangan Malaysia di Persada Dunia'),
]


# ---------- Topic = one row per Bab, pointing at its PDF ----------

def _topic_for(form_level: int, chapter_id: int, chapter_name: str) -> dict:
    """Build the topic row for one Bab.

    Filename convention matches what's already on disk, e.g.:
      static/pdfs/Form4/Bab1/Bab_1_Warisan_Negara_Bangsa.pdf
    """
    underscored = chapter_name.replace(' ', '_')
    filename = f'Bab_{chapter_id}_{underscored}.pdf'
    return {
        'form_level': form_level,
        'chapter_id': chapter_id,
        'topic_name': chapter_name,  # The Bab name is the topic name.
        'pdf_path': f'Form{form_level}/Bab{chapter_id}/{filename}',
    }


def build_topics() -> list[dict]:
    topics = []
    for cid, cname in FORM4_CHAPTERS:
        topics.append(_topic_for(4, cid, cname))
    for cid, cname in FORM5_CHAPTERS:
        topics.append(_topic_for(5, cid, cname))
    return topics


# ---------- Seeder ----------

def seed_database():
    # --- Chapters: wipe and re-insert with the real names ---
    db.session.query(TopicPage).delete()
    db.session.query(Topic).delete()
    db.session.query(Chapter).delete()
    db.session.commit()
    print('✓ Cleared chapters, topics, and topic_pages.')

    for form_level, chapters in ((4, FORM4_CHAPTERS), (5, FORM5_CHAPTERS)):
        for chapter_id, chapter_name in chapters:
            db.session.add(Chapter(
                form_level=form_level,
                chapter_id=chapter_id,
                chapter_name=chapter_name,
            ))
    db.session.commit()
    print(f'✓ Inserted {len(FORM4_CHAPTERS) + len(FORM5_CHAPTERS)} chapters.')

    # --- Topics ---
    topics = build_topics()
    for t in topics:
        db.session.add(Topic(**t, total_pages=0))
    db.session.commit()
    print(f'✓ Inserted {len(topics)} topics (one per Bab).')

    print()
    print('Next step: run `python -m scripts.ingest_pdf` to extract text from the PDFs.')


def main():
    app = create_app()
    with app.app_context():
        seed_database()


if __name__ == '__main__':
    main()

