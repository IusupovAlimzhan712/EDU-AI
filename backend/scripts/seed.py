"""
Seed the database with KSSM Sejarah Form 4 + Form 5 chapters and a
starter set of topics (matching the mock data in the frontend so the UI
shows real content immediately).

Usage:
    cd backend
    flask seed              # uses the @app.cli.command in this module
    # or directly:
    python -m scripts.seed
"""
from app import create_app
from app.extensions import db
from app.models import Chapter, Topic


# -------------------------------------------------------------------
# Chapter data — matches frontend TopicsBrowser.tsx
# -------------------------------------------------------------------

FORM4_CHAPTERS = [
    (1, 'Kemunculan Tamadun Awal Manusia'),
    (2, 'Peningkatan Tamadun'),
    (3, 'Tamadun Awal Asia Tenggara'),
    (4, 'Kemunculan Tamadun Islam dan Perkembangannya di Makkah'),
    (5, 'Kerajaan Islam di Madinah'),
    (6, 'Kerajaan Alam Melayu'),
    (7, 'Islam di Asia Tenggara'),
]

FORM5_CHAPTERS = [
    (1, 'Warisan Negara Bangsa'),
    (2, 'Kebangkitan Nasionalisme'),
    (3, 'Kemerdekaan Tanah Melayu'),
    (4, 'Penubuhan Malaysia'),
    (5, 'Pembangunan Negara'),
    (6, 'Pengukuhan Negara Bangsa'),
    (7, 'Malaysia dalam Konteks Global'),
]


# -------------------------------------------------------------------
# Topic data — a small starter set per chapter. Replace `content` with
# the real KSSM-aligned text in Phase 3 when the corpus is built.
# -------------------------------------------------------------------

TOPICS = [
    # ---- Form 4 ----
    {
        'form_level': 4, 'chapter_id': 1,
        'topic_name': 'Zaman Prasejarah',
        'content': (
            'Zaman Prasejarah merujuk kepada tempoh sebelum manusia mempunyai sistem '
            'tulisan. Tempoh ini terbahagi kepada Zaman Paleolitik, Mesolitik, '
            'Neolitik dan Logam.'
        ),
        'estimated_duration_minutes': 15,
    },
    {
        'form_level': 4, 'chapter_id': 1,
        'topic_name': 'Zaman Neolitik',
        'content': (
            'Zaman Neolitik adalah tempoh ketika manusia mula bercucuk tanam, '
            'menternak binatang dan menetap di satu tempat. Ciri-ciri penting termasuk '
            'penggunaan alatan batu yang telah dilicinkan.'
        ),
        'estimated_duration_minutes': 12,
    },
    {
        'form_level': 4, 'chapter_id': 2,
        'topic_name': 'Tamadun Mesopotamia',
        'content': (
            'Tamadun Mesopotamia terletak di antara Sungai Tigris dan Euphrates. '
            'Tamadun ini terkenal dengan sistem tulisan kuneiform, Hukum Hammurabi '
            'dan zigurat.'
        ),
        'estimated_duration_minutes': 18,
    },
    {
        'form_level': 4, 'chapter_id': 2,
        'topic_name': 'Tamadun Mesir Purba',
        'content': (
            'Tamadun Mesir Purba berkembang di sepanjang Sungai Nil. Antara pencapaian '
            'utama ialah pembinaan piramid, sistem tulisan hieroglif dan kepercayaan '
            'kepada banyak tuhan (politeisme).'
        ),
        'estimated_duration_minutes': 20,
    },
    {
        'form_level': 4, 'chapter_id': 6,
        'topic_name': 'Kesultanan Melayu Melaka',
        'content': (
            'Kesultanan Melayu Melaka diasaskan oleh Parameswara pada sekitar tahun '
            '1400. Melaka berkembang sebagai pusat perdagangan utama di Asia '
            'Tenggara dan menjadi pusat penyebaran Islam.'
        ),
        'estimated_duration_minutes': 22,
    },
    {
        'form_level': 4, 'chapter_id': 4,
        'topic_name': 'Hijrah Nabi Muhammad SAW',
        'content': (
            'Hijrah Nabi Muhammad SAW dari Makkah ke Madinah pada tahun 622 Masihi '
            'merupakan peristiwa penting dalam sejarah Islam. Perpindahan ini bukan '
            'sahaja menyelamatkan umat Islam dari penganiayaan kaum Quraisy, tetapi '
            'juga membuka lembaran baru dalam perkembangan agama Islam.'
        ),
        'estimated_duration_minutes': 25,
    },
    # ---- Form 5 ----
    {
        'form_level': 5, 'chapter_id': 1,
        'topic_name': 'Konsep Negara Bangsa',
        'content': (
            'Negara bangsa merujuk kepada sebuah entiti politik yang berdaulat, '
            'mempunyai sempadan yang jelas, kerajaan yang sah, dan rakyat yang '
            'berkongsi identiti nasional.'
        ),
        'estimated_duration_minutes': 15,
    },
    {
        'form_level': 5, 'chapter_id': 2,
        'topic_name': 'Faktor Kemunculan Nasionalisme',
        'content': (
            'Antara faktor yang mendorong kemunculan nasionalisme di Tanah Melayu '
            'ialah pengaruh agama, dasar British, perkembangan pendidikan, peranan '
            'akhbar dan majalah, serta pengaruh luar.'
        ),
        'estimated_duration_minutes': 18,
    },
    {
        'form_level': 5, 'chapter_id': 3,
        'topic_name': 'Perjanjian Persekutuan Tanah Melayu 1957',
        'content': (
            'Perjanjian Persekutuan Tanah Melayu 1957 menandakan kemerdekaan Tanah '
            'Melayu daripada British. Perjanjian ini menggariskan kuasa Yang '
            'di-Pertuan Agong, hak istimewa orang Melayu, dan kewarganegaraan.'
        ),
        'estimated_duration_minutes': 25,
    },
    {
        'form_level': 5, 'chapter_id': 4,
        'topic_name': 'Pembentukan Malaysia',
        'content': (
            'Malaysia ditubuhkan pada 16 September 1963 melalui penyatuan Persekutuan '
            'Tanah Melayu, Sabah, Sarawak dan Singapura. Singapura kemudian keluar '
            'pada tahun 1965.'
        ),
        'estimated_duration_minutes': 20,
    },
]


def seed_database():
    """Insert chapters and topics if they do not already exist."""
    # --- Chapters ---
    for form_level, chapters in (
        (4, FORM4_CHAPTERS),
        (5, FORM5_CHAPTERS),
    ):
        for chapter_id, chapter_name in chapters:
            existing = db.session.get(Chapter, (form_level, chapter_id))
            if existing:
                continue
            db.session.add(Chapter(
                form_level=form_level,
                chapter_id=chapter_id,
                chapter_name=chapter_name,
            ))
    db.session.commit()
    print(f'Seeded {len(FORM4_CHAPTERS) + len(FORM5_CHAPTERS)} chapters.')

    # --- Topics ---
    inserted = 0
    for t in TOPICS:
        existing = db.session.query(Topic).filter_by(
            form_level=t['form_level'],
            chapter_id=t['chapter_id'],
            topic_name=t['topic_name'],
        ).first()
        if existing:
            continue
        db.session.add(Topic(**t))
        inserted += 1
    db.session.commit()
    print(f'Seeded {inserted} new topics (existing topics skipped).')


def main():
    app = create_app()
    with app.app_context():
        seed_database()


if __name__ == '__main__':
    main()
