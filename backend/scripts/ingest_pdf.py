"""
Extract text from each Topic's PDF and populate topic_page + topic_chunk tables.

Usage:
    cd backend

    # Ingest ALL topics that have a pdf_path set:
    python -m scripts.ingest_pdf

    # Ingest a single topic by id:
    python -m scripts.ingest_pdf --topic 3

    # Force re-ingest even if pages already exist:
    python -m scripts.ingest_pdf --force

    # Skip embedding (faster; BM25-only retrieval until you embed later):
    python -m scripts.ingest_pdf --no-embed

Notes:
  - Uses PyMuPDF (fitz) for extraction — preserves paragraph/line structure
    significantly better than PyPDF, especially for visual timeline pages.
  - Font encoding corruption in some KSSM chapters (Bab 2, 3, 7) is corrected
    automatically via _fix_ocr_corruption(), which applies a +0x1D codepoint
    offset to affected Times-Roman glyph slots at extraction time.
  - Assumes PDFs have selectable text. Scanned/image-only PDFs will
    yield empty page rows; the script will warn but not fail.
  - Safe to re-run: existing topic_page and topic_chunk rows for a topic
    are deleted before re-inserting.
  - Embeddings are generated in batches (96 texts/call) using
    text-embedding-3-small. Each chunk ~0.0001 USD; a 50-page PDF
    with ~3 chunks/page ≈ 150 chunks ≈ $0.015.
"""
import argparse
import os
import re
import sys

import fitz  # PyMuPDF

from app import create_app
from app.extensions import db
from app.models import Topic
from app.repositories import TopicPageRepository, TopicChunkRepository

# ---------------------------------------------------------------------------
# OCR corruption correction — Times-Roman font in KSSM Bab 2 / 3 / 7
# ---------------------------------------------------------------------------
# These chapters use a subset Times-Roman font whose ToUnicode table maps
# certain glyph byte slots to codepoints that are 0x1D (29) below the
# correct ASCII value.  PyMuPDF faithfully outputs the wrong codepoint.
#
# Three classes of corruption, all sharing the same +0x1D reversal:
#
#   1. Control chars \x0B–\x1F  (never genuine in running text)
#      → always add 0x1D  e.g. \x10 → '-' (hyphen in "Austria-Hungary")
#
#   2. Symbol / digit chars 0x24–0x3C immediately before a lowercase letter
#      → word-initial capital  e.g. '3e' → 'Pe', "'u" → 'Du', '9e' → 'Ve'
#
#   3. Chars 0x44–0x5D in a Times span (always corrupted lowercase).  Genuine
#      uppercase letters are stored in the 0x24–0x3D range (Rule 2).  Covers:
#      G→d, P→m, R→o, M→j, S→p, I→f, Y→v, D→a, T→q, F→c, Z→w, [→x, \→y,
#      ]→z.  Cascade sequences like '$Perika'→'Amerika' are resolved by Rule 2
#      also triggering when the following char is itself in the 0x44–0x5D range.
#
# The correction is applied per-span, only when the span font name contains
# "Times".  All other fonts (HelveticaNeue etc.) are extracted unchanged.

_CORRUPT_FONT_MARKER = 'Times'  # font name substring that marks affected spans

# Within a Times-corrupted span, chars in the range 0x44–0x5D are always
# corrupted lowercase letters (stored value + 0x1D = correct value).
#   0x44–0x5A  'D'–'Z'  → lowercase 'a'–'w'  (mid-word consonants)
#   0x5B       '['      → 'x'  (e.g. "e[Sorti]i" → "eksploitasi")
#   0x5C       '\'      → 'y'  (e.g. "\ang" → "yang")
#   0x5D       ']'      → 'z'  (e.g. "sai]" → "saiz")
# Genuine uppercase in these spans are stored in the 0x24–0x3D range (Rule 2).
_CORRUPT_UPPER_MID = frozenset(range(0x44, 0x5E))  # 'D'–']' (0x44–0x5D)


def _apply_ocr_fix(ch: str, cp: int, prev_ch: str, next_ch: str,
                   prev_is_t: bool, next_is_t: bool, span_corrupt: bool) -> str:
    """Return the corrected character for one Times-Roman glyph, or ch if unchanged.

    span_corrupt — True when THIS SPAN contains control chars (0x0B–0x1F),
        proving its font encoding carries the +0x1D offset.  Spans without
        control chars (e.g. correctly-encoded headings on the same page) must
        not have Rule 3 applied unconditionally.

    Rule 1 — control chars \x0B–\x1F: always add 0x1D.

    Rule 2 — word-initial capital (0x24–0x3D, excl. 0x22 '"'):
        Triggers when next char is lowercase, OR when next char is itself a
        corrupted D–Z glyph in a Times span (cascade: '$Perika'→'Amerika').

    Rule 3 — chars 0x44–0x5D (D–Z, [, \\, ]):
        • span_corrupt=True → unconditional: all such chars are corrupted
          lowercase (G→d, P→m, R→o, M→j, S→p, I→f, Y→v, D→a, T→q,
          F→c, Z→w, [→x, \\→y, ]→z).
        • span_corrupt=False → bilateral context check (catches remaining
          mid-word cases while preserving genuine uppercase on clean spans).
    """
    # Rule 1
    if 0x0B <= cp <= 0x1F and ch not in '\n\r\t':
        return chr(cp + 0x1D)
    # Rule 2 — word-initial capital encoded as symbol/digit.
    # Cascade: also fire when next char is itself a corrupted D-Z glyph in a
    # Times span ('$Perika'→'Amerika').
    if 0x24 <= cp <= 0x3D and cp != 0x22:
        next_lower = next_ch.islower() or (next_is_t and ord(next_ch) in _CORRUPT_UPPER_MID)
        if next_lower:
            return chr(cp + 0x1D)
    # Rule 3
    if cp in _CORRUPT_UPPER_MID:
        if span_corrupt:
            return chr(cp + 0x1D)
        # Unconfirmed corrupt span: bilateral context with cascade awareness.
        prev_lower = (prev_ch.islower()
                      or (prev_is_t and ord(prev_ch) in _CORRUPT_UPPER_MID)
                      or (0x24 <= ord(prev_ch) <= 0x3D and ord(prev_ch) != 0x22))
        next_lower = (next_ch.islower()
                      or (next_is_t and ord(next_ch) in _CORRUPT_UPPER_MID))
        if prev_lower and (next_lower or not next_ch.isalpha()):
            return chr(cp + 0x1D)
    return ch


def _extract_page_text(page) -> str:
    """Extract page text with font-aware OCR correction.

    Uses get_text('dict') for span-level font metadata.  Spans are flattened
    per-line so cross-span context (e.g. 'gen'|'Fatan' → 'gencatan') works.

    Corruption is detected per-span (not per-page): a span is flagged corrupt
    when it contains any control char (0x0B–0x1F), proving its Times font
    encoding carries the +0x1D offset.  Different spans on the same page can
    have different encodings even with the same font name string.
    """
    parts = []
    prev_block = False
    for block in page.get_text('dict')['blocks']:
        if block.get('type') != 0:
            continue
        if prev_block:
            parts.append('\n')
        prev_block = True
        for l_idx, line in enumerate(block.get('lines', [])):
            if l_idx > 0:
                parts.append('\n')
            # Per-char tuple: (char, is_times_font, span_is_corrupt)
            # span_is_corrupt is True when the span contains any control char
            # (0x0B–0x1F), which proves its Times encoding carries the +0x1D
            # offset.  Different spans on the same page may have different
            # encodings even when they share the same font name.
            chars: list[tuple[str, bool, bool]] = []
            for span in line.get('spans', []):
                is_t = _CORRUPT_FONT_MARKER in span.get('font', '')
                raw = span.get('text', '')
                # A span is corrupt when it contains EITHER:
                #   (a) control chars 0x0B–0x1F — from digit glyphs in the corrupted
                #       font (e.g. '1'→0x14, '3'→0x16); never legitimate in prose.
                #   (b) a Rule-2 trigger: a symbol/digit glyph (0x24–0x3D, excl.
                #       0x22) immediately before a lowercase letter — the classic
                #       sign of a word-initial capital encoded via the +0x1D shift.
                #       In clean spans, '$e', '5e', '3e' etc. never occur.
                span_corrupt = is_t and (
                    any(0x0B <= ord(c) <= 0x1F and c not in '\n\r\t' for c in raw)
                    or any(
                        0x24 <= ord(raw[j]) <= 0x3D and ord(raw[j]) != 0x22
                        and raw[j + 1].islower()
                        for j in range(len(raw) - 1)
                    )
                )
                for ch in raw:
                    chars.append((ch, is_t, span_corrupt))
            n = len(chars)
            for i, (ch, is_t, span_corrupt) in enumerate(chars):
                if not is_t:
                    parts.append(ch)
                    continue
                prev_ch   = chars[i - 1][0] if i > 0     else ' '
                next_ch   = chars[i + 1][0] if i + 1 < n else ' '
                prev_is_t = chars[i - 1][1] if i > 0     else False
                next_is_t = chars[i + 1][1] if i + 1 < n else False
                parts.append(_apply_ocr_fix(
                    ch, ord(ch), prev_ch, next_ch, prev_is_t, next_is_t, span_corrupt))
    return ''.join(parts)


# Minimum words before a segment is emitted as a standalone chunk.
# Shorter segments are merged forward into the next segment.
_MIN_CHUNK_WORDS = 40

# ── Activity / exercise chunk filter ────────────────────────────────────────
# KSSM textbooks embed classroom-activity blocks (instructions, gallery walks,
# group tasks) on content pages.  These chunks contain historical keywords from
# the activity setup text (e.g. "Jelaskan pilihan raya 1955") but carry zero
# usable historical content — they pollute retrieval and crowd out real chunks.
# A chunk is classified as an activity block when it matches ANY of the signals
# below.  A single strong signal is sufficient because the patterns are highly
# specific to pedagogical text and do not appear in running historical prose.
_ACTIVITY_RE = re.compile(
    r'(?:'
    r'\bArahan\s*[:\d]'                        # "Arahan:" / "Arahan 1:"
    r'|\bmurid\b.{0,60}(?:dibahagikan|menulis|bergerak|bergilir|mencatat'
    r'|melengkapkan|membaca|mencari|menanda|menjawab|membentang)'
    r'|\bsecara\s+berkumpulan\b'               # group-work instruction
    r'|\bAktiviti\s+\d+\b'                     # "Aktiviti 1", "Aktiviti 2"
    r'|\bMembuat\s+Interpretasi\b'             # specific exercise type
    r'|\bJalan\s+Galeri\b'                     # Gallery Walk activity
    r'|\bpeta\s+minda\b'                       # mind-map task
    r')',
    re.IGNORECASE | re.DOTALL,
)


def _is_activity_chunk(text: str) -> bool:
    """Return True if the chunk is a classroom-activity instruction block.

    These blocks contain historical keywords from activity prompts but no
    usable historical prose; excluding them improves retrieval precision.
    """
    return bool(_ACTIVITY_RE.search(text))

# Structural noise: "BAB"/"BAB 2"/"7 BAB" headings and section reference codes
# like "4.2".  These add no retrievable content.
#
# Bare 1–3 digit lines (page-number footers) are intentionally NOT stripped here.
# Table cell values (e.g. "2", "9" for kerusi counts) are indistinguishable from
# page-number footers without full layout analysis, and stripping them destroys
# table data.  Page-number lines contribute negligible retrieval noise since they
# appear in chunks that also contain substantive content.
_NOISE_LINE_RE = re.compile(
    r'^(?:'
    r'(?:\d+\s+)?BAB(?:\s+\d+)?'      # BAB, BAB 2, 4 BAB, 7 BAB
    r'|\d+\.\d+'                        # section refs  e.g. 4.2, 3.1
    r')$',
    re.IGNORECASE,
)

# Section headers are short (1–6 words), title-case, no trailing sentence punct.
_MAX_HEADER_WORDS = 6


def _is_section_header(line: str) -> bool:
    """Return True if *line* looks like a textbook section heading.

    Detects patterns such as:
      "Latar Belakang", "Gagasan Malayan Union", "Kesatuan Melayu Muda",
      "Parti Kebangsaan Melayu Malaya", "Latar Belakang Perang Dunia"
    """
    line = line.strip()
    if not line or _NOISE_LINE_RE.match(line):
        return False
    words = line.split()
    if not (1 <= len(words) <= _MAX_HEADER_WORDS):
        return False
    # Sentence-ending punctuation means it is a statement, not a heading
    if line[-1] in '.?!,;:':
        return False
    # Bullet / list markers are never section headings
    if words[0] in ('•', '-', '*', '–', '—'):
        return False
    # Numbered list items  (1.  2.  a.  b.)
    if re.match(r'^\d+[\.\)]\s', line) or re.match(r'^[a-z][\.\)]\s', line):
        return False
    # Must start with an uppercase letter
    if not line[0].isupper():
        return False
    # Must contain at least one alphabetic character (rules out pure-number lines
    # that survived _NOISE_LINE_RE, such as 4-digit years like 1914)
    if not any(c.isalpha() for c in line):
        return False
    return True


def find_pdf_root(app) -> str:
    backend_root = os.path.dirname(app.root_path)
    return os.path.join(backend_root, 'static', 'pdfs')


def _split_into_chunks(text: str, min_words: int = _MIN_CHUNK_WORDS) -> list[str]:
    """Structure-aware chunker for KSSM textbook pages extracted by PyMuPDF.

    Algorithm
    ---------
    1. Strip noise lines (page numbers, "BAB N", section codes).
    2. Walk every line looking for section-header split points.  A split is
       inserted *before* a header line when:
         (a) the preceding content line ends a sentence  (.?!), or
         (b) the preceding line is itself a section header (two headers in a
             row always marks a new section).
    3. Group the lines between split points into raw segments.
    4. Merge consecutive segments forward until the accumulated word count
       reaches *min_words*, then emit a chunk.  Any final leftover is
       appended to the last chunk rather than emitted as a stub.

    Newlines within a segment are preserved so the LLM sees textbook
    structure (timeline entries, bullet lists, section subheadings).
    """
    if not text or not text.strip():
        return []

    # 1. Clean lines
    raw_lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in raw_lines if l and not _NOISE_LINE_RE.match(l)]
    if not lines:
        return []

    # 2. Find split points
    split_at: set[int] = set()
    for i in range(1, len(lines)):
        if not _is_section_header(lines[i]):
            continue
        prev = lines[i - 1]
        if prev and prev[-1] in '.?!':
            split_at.add(i)
        elif _is_section_header(prev):
            # Two consecutive headers → new section starts at this header
            split_at.add(i)

    # 3. Build raw segment list
    raw_segments: list[list[str]] = []
    current: list[str] = []
    for i, line in enumerate(lines):
        if i in split_at:
            raw_segments.append(current)
            current = []
        current.append(line)
    raw_segments.append(current)

    # 4. Merge short segments and emit chunks
    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0

    for seg in raw_segments:
        seg_text = '\n'.join(seg)
        w = len(seg_text.split())
        if w == 0:
            continue
        buf.append(seg_text)
        buf_words += w
        if buf_words >= min_words:
            chunks.append('\n'.join(buf).strip())
            buf = []
            buf_words = 0

    # Flush remaining partial buffer
    if buf:
        leftover = '\n'.join(buf).strip()
        if chunks:
            chunks[-1] = chunks[-1] + '\n' + leftover
        else:
            chunks.append(leftover)

    return [c for c in chunks if c.strip()]


def ingest_topic(topic: Topic, pdf_root: str, force: bool, embed: bool) -> bool:
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
        doc = fitz.open(abs_path)
        # Suppress PyMuPDF's "Ignoring wrong pointing object" warnings that
        # appear for PDFs with malformed cross-reference tables (harmless).
        fitz.TOOLS.mupdf_warnings()
    except Exception as exc:
        print(f'  ✗ Topic {topic.topic_id}: failed to read PDF: {exc}')
        return False

    # Clear existing rows
    if existing:
        TopicPageRepository.delete_all_for_topic(topic.topic_id)
    TopicChunkRepository.delete_all_for_topic(topic.topic_id)

    # ── Page rows ──────────────────────────────────────────────────────
    page_rows = []
    empty_pages = 0
    for i in range(len(doc)):
        try:
            text = _extract_page_text(doc[i])
            # Clear per-page warnings to avoid accumulation
            fitz.TOOLS.mupdf_warnings()
        except Exception:
            text = ''
        text = text.strip()
        if not text:
            empty_pages += 1
        page_rows.append({
            'topic_id':    topic.topic_id,
            'page_number': i + 1,
            'text_content': text,
            'word_count':  len(text.split()),
        })
    doc.close()

    TopicPageRepository.bulk_insert(page_rows)
    topic.total_pages = len(page_rows)

    # ── Chunk rows ─────────────────────────────────────────────────────
    chunk_texts: list[str] = []
    chunk_meta: list[dict] = []   # parallel list of metadata dicts

    activity_chunks_skipped = 0
    for pr in page_rows:
        if not pr['text_content']:
            continue
        paragraphs = _split_into_chunks(pr['text_content'])
        idx = 0
        for para in paragraphs:
            if _is_activity_chunk(para):
                activity_chunks_skipped += 1
                continue
            chunk_texts.append(para)
            chunk_meta.append({
                'topic_id':    topic.topic_id,
                'page_number': pr['page_number'],
                'chunk_index': idx,
                'text_content': para,
                'word_count':  len(para.split()),
                'embedding':   None,
            })
            idx += 1

    # ── Embed (optional) ───────────────────────────────────────────────
    if embed and chunk_texts:
        try:
            from app.services.ai.embedding_service import (
                embed_texts, serialize_embedding,
            )
            from flask import current_app

            api_key = current_app.config['OPENAI_API_KEY']
            print(f'     Embedding {len(chunk_texts)} chunks …', end='', flush=True)
            vecs = embed_texts(chunk_texts, api_key)
            for meta, vec in zip(chunk_meta, vecs):
                meta['embedding'] = serialize_embedding(vec)
            print(f' done.')
        except Exception as exc:
            print(f'\n  ⚠ Embedding failed ({exc}); chunks stored without vectors.')

    TopicChunkRepository.bulk_insert(chunk_meta)
    db.session.commit()

    status = (
        f'  ✓ Topic {topic.topic_id} ({topic.topic_name}): '
        f'{len(page_rows)} pages, {len(chunk_texts)} chunks'
    )
    embedded_count = sum(1 for m in chunk_meta if m['embedding'] is not None)
    if embedded_count:
        status += f' ({embedded_count} embedded)'
    if activity_chunks_skipped:
        status += f' [{activity_chunks_skipped} activity chunks skipped]'
    if empty_pages:
        status += f' [warning: {empty_pages} empty pages — likely scanned/image-only]'
    print(status)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=int, help='Ingest only this topicId')
    parser.add_argument('--force', action='store_true',
                        help='Re-ingest topics that already have pages')
    parser.add_argument('--no-embed', action='store_true',
                        help='Skip OpenAI embedding (BM25-only retrieval)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Ensure topic_chunk table exists without requiring a full migration
        from app.models.topic_chunk import TopicChunk
        TopicChunk.__table__.create(db.engine, checkfirst=True)

        pdf_root = find_pdf_root(app)
        print(f'PDF root: {pdf_root}')

        q = db.session.query(Topic)
        if args.topic:
            q = q.filter(Topic.topic_id == args.topic)
        topics = q.all()
        if not topics:
            print('No topics matched.')
            sys.exit(0)

        embed = not args.no_embed
        ingested = 0
        for t in topics:
            if ingest_topic(t, pdf_root, args.force, embed):
                ingested += 1
        print()
        print(f'Done. {ingested}/{len(topics)} topics ingested.')


if __name__ == '__main__':
    main()
