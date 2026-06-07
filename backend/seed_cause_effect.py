"""
Generate and seed cause-effect diagrams for all chapters.

Uses GPT-4o-mini to produce a Mermaid.js flowchart (causes → event → effects)
for each chapter, grounded in the chapter's topic text content.

Usage (from the backend/ directory):
    python seed_cause_effect.py           # all form levels
    python seed_cause_effect.py 4         # Form 4 only
    python seed_cause_effect.py 5         # Form 5 only
    python seed_cause_effect.py --regen   # overwrite existing diagrams
"""
import sys
import re
import logging
from openai import OpenAI

from app import create_app
from app.extensions import db
from app.models import Chapter, CauseEffectDiagram
from app.repositories import TopicPageRepository

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

client = OpenAI()

PROMPT_TEMPLATE = """You are generating a Mermaid.js flowchart diagram for Malaysian SPM Sejarah (History).

Chapter: {chapter_name} (Form {form_level}, Bab {chapter_id})

Chapter content summary (first 1500 words of topic text):
\"\"\"
{content}
\"\"\"

Generate a Mermaid flowchart LR diagram showing SEBAB (causes) → PERISTIWA UTAMA (central event) → AKIBAT (effects).

Rules:
- Use BAHASA MALAYSIA for all node labels
- 3 to 5 CAUSE nodes on the left (prefix node IDs with C)
- 1 CENTRAL EVENT node in the middle (node ID: E)
- 3 to 4 EFFECT nodes on the right (prefix node IDs with EF)
- Keep each label SHORT: max 6 words, use \\n to break long labels
- Node IDs must be plain alphanumeric (e.g. C1, C2, E, EF1)
- Include classDef and class assignment lines exactly as shown in the example
- Output ONLY the Mermaid code — no markdown fences, no explanation

Example format:
flowchart LR
    C1["Tanah Subur\\nBerlimpah"] --> E["Perkembangan\\nTamadun Awal"]
    C2["Laluan Sungai\\nUtama"] --> E
    C3["Iklim Sesuai\\nuntuk Pertanian"] --> E
    E --> EF1["Pertanian\\nBerkembang"]
    E --> EF2["Perdagangan\\nAktif"]
    E --> EF3["Sistem Sosial\\nTerbentuk"]
    classDef cause fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,font-size:13px
    classDef event fill:#1E3A8A,stroke:#1E3A8A,color:#ffffff,font-weight:bold,font-size:14px
    classDef effect fill:#D1FAE5,stroke:#059669,color:#065F46,font-size:13px
    class C1,C2,C3 cause
    class E event
    class EF1,EF2,EF3 effect
"""


def get_chapter_content(form_level: int, chapter_id: int) -> str:
    """Retrieve up to ~1500 words of text content for a chapter."""
    pages = TopicPageRepository.list_for_chapter(form_level, chapter_id)
    texts = [p.text_content for p in pages if p.text_content and p.text_content.strip()]
    combined = ' '.join(texts)
    words = combined.split()
    return ' '.join(words[:1500])


def validate_mermaid(source: str) -> bool:
    """Basic validation: must start with flowchart and contain E node."""
    s = source.strip()
    if not s.startswith('flowchart'):
        return False
    if '["' not in s and "E[" not in s:
        return False
    if 'classDef' not in s:
        return False
    return True


def generate_diagram(chapter: Chapter, content: str) -> tuple[str, str]:
    """Call GPT-4o-mini and return (title, mermaid_source). Retries up to 3x."""
    title = f"Sebab dan Akibat: {chapter.chapter_name}"
    prompt = PROMPT_TEMPLATE.format(
        chapter_name=chapter.chapter_name,
        form_level=chapter.form_level,
        chapter_id=chapter.chapter_id,
        content=content,
    )

    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert in Malaysian SPM Sejarah curriculum. '
                            'You generate valid Mermaid.js diagrams only — no prose, no fences.'
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            source = resp.choices[0].message.content.strip()
            # Strip any accidental markdown fences
            source = re.sub(r'^```[a-z]*\n?', '', source)
            source = re.sub(r'\n?```$', '', source)
            source = source.strip()

            if validate_mermaid(source):
                return title, source
            else:
                logger.warning(
                    'Attempt %d: invalid Mermaid output for F%d-Ch%d, retrying…',
                    attempt, chapter.form_level, chapter.chapter_id,
                )
        except Exception as e:
            logger.error('Attempt %d: OpenAI error: %s', attempt, e)

    raise RuntimeError(
        f'Failed to generate valid diagram for F{chapter.form_level}-Ch{chapter.chapter_id} after 3 attempts'
    )


def seed(form_levels: list[int], regen: bool = False) -> None:
    app = create_app()
    with app.app_context():
        chapters = db.session.query(Chapter).filter(
            Chapter.form_level.in_(form_levels)
        ).order_by(Chapter.form_level, Chapter.chapter_id).all()

        logger.info('Found %d chapters to process.', len(chapters))
        ok = 0
        skipped = 0
        failed = 0

        for ch in chapters:
            existing = db.session.query(CauseEffectDiagram).filter_by(
                form_level=ch.form_level, chapter_id=ch.chapter_id
            ).first()

            if existing and not regen:
                logger.info('SKIP F%d-Ch%d %s (already exists)', ch.form_level, ch.chapter_id, ch.chapter_name)
                skipped += 1
                continue

            content = get_chapter_content(ch.form_level, ch.chapter_id)
            if not content.strip():
                logger.warning('SKIP F%d-Ch%d %s (no text content)', ch.form_level, ch.chapter_id, ch.chapter_name)
                skipped += 1
                continue

            logger.info('Generating F%d-Ch%d %s…', ch.form_level, ch.chapter_id, ch.chapter_name)
            try:
                title, source = generate_diagram(ch, content)
                if existing:
                    existing.title = title
                    existing.mermaid_source = source
                else:
                    db.session.add(CauseEffectDiagram(
                        form_level=ch.form_level,
                        chapter_id=ch.chapter_id,
                        title=title,
                        mermaid_source=source,
                    ))
                db.session.commit()
                logger.info('OK F%d-Ch%d', ch.form_level, ch.chapter_id)
                ok += 1
            except Exception as e:
                db.session.rollback()
                logger.error('FAIL F%d-Ch%d: %s', ch.form_level, ch.chapter_id, e)
                failed += 1

        logger.info('Done. ok=%d skipped=%d failed=%d', ok, skipped, failed)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    regen = '--regen' in sys.argv

    if args:
        levels = [int(a) for a in args if a in ('4', '5')]
    else:
        levels = [4, 5]

    seed(levels, regen=regen)
