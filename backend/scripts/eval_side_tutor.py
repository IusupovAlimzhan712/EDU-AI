"""
Side Tutor end-to-end evaluation harness.

Instruments retrieval + prompt construction without modifying prod code.
Runs a test matrix across page types and question categories, then
prints a structured failure report.

Usage:
    cd backend
    python -m scripts.eval_side_tutor
    python -m scripts.eval_side_tutor --topic 21 --pages 5,6
    python -m scripts.eval_side_tutor --dry-run   # retrieval only, no LLM
"""
import argparse
import json
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Optional

# ── Test matrix ──────────────────────────────────────────────────────────────
#
# Each entry: (topic_id, page, page_type_label, questions)
# Questions: (category, question_text, expected_pass_hint)
#   category:  "factual" | "attribution_yes" | "attribution_no" | "explain" | "general"
#   expected_pass_hint: substring that should appear (None = manual check)

TEST_MATRIX = [
    # ── TIMELINE pages ────────────────────────────────────────────────────
    {
        'label': 'TIMELINE (corrupted) — Nasionalisme pg1',
        'topic_id': 19,
        'page': 1,
        'page_type': 'timeline',
        'questions': [
            ('general',        'Apa yang dinyatakan pada halaman ini?', None),
            ('attribution_yes','Adakah Revolusi Amerika dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah Revolusi Meiji dinyatakan pada halaman ini?', 'Tidak'),
            ('factual',        'Bilakah Revolusi Amerika berlaku?', '1776'),
            ('explain',        'Terangkan perkembangan nasionalisme di Barat.', None),
        ],
    },
    {
        'label': 'TIMELINE (corrupted) — Nasionalisme pg2',
        'topic_id': 19,
        'page': 2,
        'page_type': 'timeline',
        'questions': [
            ('general',        'Apa yang dinyatakan pada halaman ini?', None),
            ('attribution_yes','Adakah Revolusi Meiji dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah Revolusi Amerika dinyatakan pada halaman ini?', 'Tidak'),
            ('factual',        'Apakah Revolusi Meiji?', 'Meiji'),
        ],
    },
    {
        'label': 'TIMELINE (corrupted) — Perang Dunia pg1',
        'topic_id': 20,
        'page': 1,
        'page_type': 'timeline',
        'questions': [
            ('general',        'Apa yang dinyatakan pada halaman ini?', None),
            ('attribution_yes','Adakah Perang Dunia Pertama dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah serangan Jepun ke Tanah Melayu dinyatakan pada halaman ini?', 'Tidak'),
            ('factual',        'Bila Perang Dunia Pertama bermula?', None),
        ],
    },
    # ── SYNOPSIS pages ────────────────────────────────────────────────────
    {
        'label': 'SYNOPSIS — Era Pentadbiran Britania pg1',
        'topic_id': 21,
        'page': 1,
        'page_type': 'synopsis',
        'questions': [
            ('general',        'Apakah sinopsis bab ini?', None),
            ('attribution_yes','Adakah BMA dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah ciri-ciri Malayan Union dinyatakan pada halaman ini?', 'Tidak'),
            ('factual',        'Apakah itu BMA?', 'Tentera British'),
        ],
    },
    {
        'label': 'SYNOPSIS — PTM 1948 pg1',
        'topic_id': 22,
        'page': 1,
        'page_type': 'synopsis',
        'questions': [
            ('general',        'Apa yang dinyatakan pada halaman ini?', None),
            ('attribution_yes','Adakah Persekutuan Tanah Melayu 1948 disebut pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah ciri-ciri Persekutuan Tanah Melayu dinyatakan pada halaman ini?', 'Tidak'),
        ],
    },
    # ── CONCEPT-DEFINITION pages ──────────────────────────────────────────
    {
        'label': 'CONCEPT-DEF — Malayan Union (ciri-ciri) pg6',
        'topic_id': 21,
        'page': 6,
        'page_type': 'concept_definition',
        'questions': [
            ('factual',        'Apakah ciri-ciri Perlembagaan Malayan Union?', None),
            ('attribution_yes','Adakah sistem kewarganegaraan dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah misi MacMichael dinyatakan pada halaman ini?', 'Tidak'),
            ('explain',        'Mengapa sistem kewarganegaraan Malayan Union ditentang?', None),
        ],
    },
    {
        'label': 'CONCEPT-DEF — ciri-ciri PTM 1948 pg11',
        'topic_id': 22,
        'page': 11,
        'page_type': 'concept_definition',
        'questions': [
            ('factual',        'Apakah ciri-ciri Persekutuan Tanah Melayu 1948?', None),
            ('attribution_yes','Adakah ciri-ciri Persekutuan Tanah Melayu dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah Hartal dinyatakan pada halaman ini?', 'Tidak'),
        ],
    },
    # ── SUMMARY / IMBAS KEMBALI pages ─────────────────────────────────────
    {
        'label': 'SUMMARY — Era Pentadbiran Britania pg27',
        'topic_id': 21,
        'page': 27,
        'page_type': 'summary',
        'questions': [
            ('general',        'Apakah kandungan halaman ini?', None),
            ('attribution_yes','Adakah BMA disebut pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah misi MacMichael dinyatakan secara terperinci pada halaman ini?', 'Tidak'),
            ('factual',        'Senaraikan topik utama dalam bab ini.', None),
        ],
    },
    {
        'label': 'SUMMARY — PTM 1948 pg15',
        'topic_id': 22,
        'page': 15,
        'page_type': 'summary',
        'questions': [
            ('general',        'Apakah kandungan halaman ini?', None),
            ('attribution_yes','Adakah faktor penubuhan PTM 1948 dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah ciri-ciri PTM 1948 dinyatakan secara terperinci pada halaman ini?', 'Tidak'),
        ],
    },
    # ── MAP pages ─────────────────────────────────────────────────────────
    {
        'label': 'MAP — Perang Dunia Kedua di Eropah pg12',
        'topic_id': 20,
        'page': 12,
        'page_type': 'map',
        'questions': [
            ('general',        'Apa yang ditunjukkan pada halaman ini?', None),
            ('attribution_yes','Adakah nama bandar seperti Moscow dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah sebab Perang Dunia Kedua dinyatakan pada halaman ini?', 'Tidak'),
            ('factual',        'Negara mana yang disebut dalam peta ini?', None),
        ],
    },
    # ── DIAGRAM pages ─────────────────────────────────────────────────────
    {
        'label': 'DIAGRAM — Tiga Badan Pemerintahan pg17',
        'topic_id': 30,
        'page': 17,
        'page_type': 'diagram',
        'questions': [
            ('general',        'Apa yang dinyatakan pada halaman ini?', None),
            ('attribution_yes','Adakah Badan Perundangan dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah fungsi Badan Kehakiman dinyatakan secara terperinci pada halaman ini?', 'Tidak'),
            ('explain',        'Terangkan pembahagian kuasa antara tiga badan pemerintahan.', None),
        ],
    },
    # ── RICH CONTENT pages (clean text) ───────────────────────────────────
    {
        'label': 'RICH TEXT — MacMichael Mission pg7',
        'topic_id': 21,
        'page': 7,
        'page_type': 'rich_text',
        'questions': [
            ('factual',        'Siapakah Sir Harold MacMichael?', 'MacMichael'),
            ('factual',        'Apakah tujuan misi MacMichael?', None),
            ('attribution_yes','Adakah misi MacMichael dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah penentangan orang Melayu terhadap Malayan Union dinyatakan pada halaman ini?', 'Tidak'),
            ('explain',        'Mengapa MacMichael berjaya mendapat tandatangan Sultan?', None),
        ],
    },
    {
        'label': 'RICH TEXT — Penentangan Rakyat pg12',
        'topic_id': 21,
        'page': 12,
        'page_type': 'rich_text',
        'questions': [
            ('factual',        'Siapakah tokoh wanita yang menentang Malayan Union?', None),
            ('attribution_yes','Adakah bantahan wanita dinyatakan pada halaman ini?', 'Ya'),
            ('attribution_no', 'Adakah gagasan Malayan Union dijelaskan pada halaman ini?', 'Tidak'),
            ('explain',        'Bagaimana wanita terlibat dalam penentangan Malayan Union?', None),
        ],
    },
]


@dataclass
class RetrievalDiag:
    chunks: list = field(default_factory=list)
    top_bm25_score: int = 0
    is_page_ref: bool = False
    page_injected: bool = False
    sim_floor_dropped: int = 0
    fallback_used: str = ''
    source_pages: list = field(default_factory=list)
    context_length: int = 0
    context_preview: str = ''


@dataclass
class TestResult:
    label: str
    topic_id: int
    page: int
    page_type: str
    category: str
    question: str
    expected_hint: Optional[str]
    retrieval: RetrievalDiag
    response: str
    status: str        # 'pass' | 'fail' | 'warn' | 'error' | 'skip'
    failure_class: str  # '' | 'retrieval' | 'grounding' | 'prompt' | 'attribution' | 'ingestion' | 'ui'
    notes: str


def run_retrieval_diag(app, topic_id: int, page: int, question: str) -> RetrievalDiag:
    """Run retrieval pipeline and capture diagnostics without calling LLM."""
    from app.extensions import db
    from app.repositories import TopicChunkRepository, TopicPageRepository
    from app.services.tutor_service import (
        _is_page_referential, _inject_current_page,
        _apply_similarity_filter, _strip_internal,
        _CONFIDENCE_THRESHOLD,
    )
    from app.models import Topic

    diag = RetrievalDiag()

    with app.app_context():
        topic = db.session.get(Topic, topic_id)
        if not topic:
            diag.fallback_used = 'topic_not_found'
            return diag

        # Hybrid retrieval
        raw, top_score = TopicChunkRepository.search_hybrid(
            topic_ids=[topic_id], query=question, limit=8
        )
        diag.top_bm25_score = top_score

        # Store raw chunks with _sim before stripping
        for c in raw:
            diag.chunks.append({
                'page': c.get('page_number'),
                'sim': c.get('_sim'),
                'text_preview': (c.get('text_content') or '')[:80],
            })

        # Similarity filter
        if raw:
            filtered = _apply_similarity_filter(raw)
            diag.sim_floor_dropped = len(raw) - len(filtered)
            raw = filtered

        # Page referential?
        diag.is_page_ref = _is_page_referential(question)
        if diag.is_page_ref:
            pre_len = len(raw)
            raw = _inject_current_page(raw, topic_id, page)
            diag.page_injected = len(raw) > pre_len

        # Fallback paths
        if not raw:
            raw, top_score = TopicPageRepository.search_relevant_scored(
                topic_ids=[topic_id], query=question, limit=8
            )
            diag.fallback_used = 'page_bm25'

        if not raw:
            for p in (page - 1, page, page + 1):
                if p >= 1:
                    row = TopicPageRepository.get(topic_id, p)
                    if row and row.text_content:
                        raw.append({'page_number': p, 'text_content': row.text_content})
            diag.fallback_used = 'current_page_window'

        # Strip internal keys
        raw = _strip_internal(raw)
        diag.source_pages = sorted(set(r['page_number'] for r in raw))
        context = '\n\n'.join(
            f'[Halaman {r["page_number"]}]\n{r["text_content"]}' for r in raw
        )
        diag.context_length = len(context)
        diag.context_preview = context[:300]

    return diag


def run_llm_test(app, topic_id: int, page: int, question: str) -> tuple[str, str]:
    """Run full Side Tutor pipeline and return (response_text, status)."""
    from app.services.tutor_service import TutorService

    response_parts = []
    final_status = 'error'
    with app.app_context():
        try:
            for evt in TutorService.stream_reply(
                student_id=1,
                topic_id=topic_id,
                question=question,
                current_page=page,
            ):
                if evt.get('event') == 'token':
                    response_parts.append(evt.get('chunk', ''))
                elif evt.get('event') == 'final':
                    response_parts = [evt.get('content', '')]
                    final_status = evt.get('validation_status', 'ok')
                elif evt.get('event') == 'error':
                    return f"[ERROR] {evt.get('message')}", 'error'
        except Exception as exc:
            return f"[EXCEPTION] {exc}", 'error'

    return ''.join(response_parts), final_status


def classify_result(
    category: str,
    expected_hint: Optional[str],
    response: str,
    diag: RetrievalDiag,
) -> tuple[str, str, str]:
    """Returns (status, failure_class, notes)."""
    notes_parts = []

    # Retrieval observations
    current_page_in_sources = diag.source_pages  # will be checked per test
    if diag.sim_floor_dropped > 0:
        notes_parts.append(f'sim_filter dropped {diag.sim_floor_dropped} chunks (safety fallback active)')
    if diag.fallback_used:
        notes_parts.append(f'fallback={diag.fallback_used}')
    if diag.page_injected:
        notes_parts.append('current-page injected')

    # Hint-based pass/fail for attribution questions
    if expected_hint is not None:
        resp_lower = response.lower()
        hint_lower = expected_hint.lower()
        if expected_hint == 'Tidak':
            # Should say tidak / not present
            if 'tidak' in resp_lower or 'tiada' in resp_lower or 'not' in resp_lower:
                status = 'pass'
                failure_class = ''
            else:
                status = 'fail'
                # Diagnose: did the retrieved context contain current page?
                failure_class = 'attribution'
                notes_parts.append('Expected "Tidak" but response does not contain denial')
        elif expected_hint == 'Ya':
            if 'tidak' in resp_lower[:50]:
                status = 'fail'
                failure_class = 'attribution'
                notes_parts.append('Expected "Ya" but response starts with denial')
            else:
                status = 'pass'
                failure_class = ''
        elif hint_lower in resp_lower:
            status = 'pass'
            failure_class = ''
        else:
            status = 'warn'
            failure_class = ''
            notes_parts.append(f'Expected hint "{expected_hint}" not found in response')
    else:
        status = 'warn'
        failure_class = ''
        notes_parts.append('manual check required')

    # Additional failure classification
    if status == 'fail':
        # Was the current page not retrieved at all?
        # (diag.source_pages not populated here — done at call site)
        pass

    return status, failure_class, '; '.join(notes_parts)


PASS  = '\033[92m✓\033[0m'
FAIL  = '\033[91m✗\033[0m'
WARN  = '\033[93m?\033[0m'
ERROR = '\033[91m!\033[0m'

STATUS_ICONS = {'pass': PASS, 'fail': FAIL, 'warn': WARN, 'error': ERROR, 'skip': '–'}


def fmt_response(text: str, width: int = 100) -> str:
    lines = []
    for line in text.split('\n'):
        lines.extend(textwrap.wrap(line, width) or [''])
    return '\n    '.join(lines[:12])  # cap at 12 lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=int, help='Only run tests for this topic_id')
    parser.add_argument('--pages', help='Comma-separated page numbers to test')
    parser.add_argument('--dry-run', action='store_true',
                        help='Retrieval diagnostics only — no LLM calls')
    parser.add_argument('--category', help='Only run this question category')
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    pages_filter = set(int(p) for p in args.pages.split(',')) if args.pages else None

    results: list[TestResult] = []
    pass_count = fail_count = warn_count = error_count = 0

    for test_case in TEST_MATRIX:
        tid = test_case['topic_id']
        pg = test_case['page']

        if args.topic and tid != args.topic:
            continue
        if pages_filter and pg not in pages_filter:
            continue

        print(f"\n{'═'*80}")
        print(f"  {test_case['label']}")
        print(f"  topic={tid}  page={pg}  type={test_case['page_type']}")
        print(f"{'─'*80}")

        for category, question, expected_hint in test_case['questions']:
            if args.category and category != args.category:
                continue

            print(f"\n  [{category}] {question}")

            # ── Retrieval diagnostics ───────────────────────────────────
            diag = run_retrieval_diag(app, tid, pg, question)

            print(f"  Retrieval: bm25_top={diag.top_bm25_score} "
                  f"is_page_ref={diag.is_page_ref} "
                  f"page_injected={diag.page_injected} "
                  f"sim_dropped={diag.sim_floor_dropped} "
                  f"fallback={diag.fallback_used or 'none'}")
            print(f"  Sources:   pages={diag.source_pages}")
            print(f"  Chunks retrieved ({len(diag.chunks)}):")
            for i, c in enumerate(diag.chunks[:8]):
                sim_str = f"sim={c['sim']:.3f}" if c['sim'] is not None else "sim=N/A"
                print(f"    [{i+1}] pg={c['page']}  {sim_str}  | {c['text_preview']}")

            if args.dry_run:
                results.append(TestResult(
                    label=test_case['label'], topic_id=tid, page=pg,
                    page_type=test_case['page_type'], category=category,
                    question=question, expected_hint=expected_hint,
                    retrieval=diag, response='(dry run)',
                    status='skip', failure_class='', notes='dry-run',
                ))
                print('  → DRY RUN (no LLM call)')
                continue

            # ── LLM call ───────────────────────────────────────────────
            print('  Calling LLM …', end='', flush=True)
            response, llm_status = run_llm_test(app, tid, pg, question)
            print(' done')

            status, failure_class, notes = classify_result(
                category, expected_hint, response, diag
            )

            # Refine failure classification with retrieval context
            if status == 'fail' and failure_class == 'attribution':
                if pg not in diag.source_pages:
                    notes += f'; current page {pg} NOT in retrieved pages → retrieval issue'
                    failure_class = 'retrieval'
                elif diag.sim_floor_dropped > 0:
                    notes += '; sim_filter safety fallback included out-of-scope chunks → grounding issue'
                    failure_class = 'grounding'

            icon = STATUS_ICONS.get(status, '?')
            print(f"  {icon} [{status.upper()}]  failure_class={failure_class or 'N/A'}")
            if notes:
                print(f"     Notes: {notes}")
            print(f"  Response:")
            print(f"    {fmt_response(response)}")

            r = TestResult(
                label=test_case['label'], topic_id=tid, page=pg,
                page_type=test_case['page_type'], category=category,
                question=question, expected_hint=expected_hint,
                retrieval=diag, response=response,
                status=status, failure_class=failure_class, notes=notes,
            )
            results.append(r)

            if status == 'pass':   pass_count  += 1
            elif status == 'fail': fail_count  += 1
            elif status == 'warn': warn_count  += 1
            else:                  error_count += 1

    # ── Summary report ───────────────────────────────────────────────────
    print(f"\n\n{'═'*80}")
    print('  EVALUATION SUMMARY')
    print(f"{'═'*80}")
    total = pass_count + fail_count + warn_count + error_count
    print(f"  Total: {total}   Pass: {pass_count}   Fail: {fail_count}   "
          f"Warn(manual): {warn_count}   Error: {error_count}")

    if fail_count or error_count:
        print(f"\n  FAILURES & ERRORS:")
        for r in results:
            if r.status in ('fail', 'error'):
                print(f"\n  {STATUS_ICONS[r.status]} [{r.page_type}] {r.label}")
                print(f"     question:       {r.question}")
                print(f"     category:       {r.category}")
                print(f"     failure_class:  {r.failure_class}")
                print(f"     source_pages:   {r.retrieval.source_pages}")
                print(f"     is_page_ref:    {r.retrieval.is_page_ref}")
                print(f"     page_injected:  {r.retrieval.page_injected}")
                print(f"     sim_dropped:    {r.retrieval.sim_floor_dropped}")
                print(f"     notes:          {r.notes}")
                print(f"     response:       {r.response[:200]}")

    # Failure class breakdown
    from collections import Counter
    fc = Counter(r.failure_class for r in results if r.status in ('fail','error') and r.failure_class)
    if fc:
        print(f"\n  FAILURE CLASS BREAKDOWN:")
        for cls, cnt in fc.most_common():
            print(f"    {cls:<20} {cnt}")

    # Page type breakdown
    pt = Counter(r.page_type for r in results if r.status in ('fail','error'))
    if pt:
        print(f"\n  PAGE TYPE FAILURE BREAKDOWN:")
        for ptype, cnt in pt.most_common():
            print(f"    {ptype:<25} {cnt}")

    print()


if __name__ == '__main__':
    main()
