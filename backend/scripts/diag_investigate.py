"""
Diagnostic investigation script for three observed inconsistencies in General Tutor.

Issue 1: "Siapakah Hans Kohn?" → "tidak dinyatakan"
Issue 2: "Apakah peristiwa yang berlaku pada tahun 1776?" → "tidak dinyatakan"
Issue 3: "Apakah maksud jus soli?" gives inconsistent answers
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

DIVIDER = "=" * 70
_SIM_THRESHOLD = 0.50
_CONFIDENCE_THRESHOLD = 3


def retrieve_and_filter(question, limit=10):
    with app.app_context():
        from app.repositories import TopicChunkRepository
        from app.services.tutor_service import _apply_similarity_filter
        from app.extensions import db
        from app.models import Topic

        all_topic_ids = [t.topic_id for t in db.session.query(Topic.topic_id).all()]
        raw_chunks, top_score = TopicChunkRepository.search_hybrid(
            topic_ids=all_topic_ids,
            query=question,
            limit=limit,
        )
        filtered = _apply_similarity_filter(raw_chunks)
        return raw_chunks, filtered, top_score


def describe_chunk(c, idx):
    sim = c.get('_sim')
    sim_str = f"{sim:.3f}" if sim is not None else "None"
    topic = c.get('topic_id', '?')
    page = c.get('page_number', '?')
    cidx = c.get('chunk_idx', '?')
    text_preview = c.get('text_content', '')[:100].replace('\n', ' ')
    return f"  [{idx}] t={topic} pg={page} idx={cidx} sim={sim_str} | {text_preview!r}"


def run_single_trace(question, label=None):
    lbl = label or question
    print(f"\n{'─'*60}")
    print(f"Q: {lbl}")

    raw_chunks, filtered, top_score = retrieve_and_filter(question)

    with app.app_context():
        from app.services.ai.entity_gate import detect_expected_entity_type, context_has_entity
        from app.services.ai.question_classifier import classify_question
        from app.services.ai.sentence_extractor import extract_for_mode, MODE_SENTENCE_BUDGET

        entity_type = detect_expected_entity_type(question)
        mode = classify_question(question)

        ctx_all = " ".join(c.get('text_content', '') for c in raw_chunks)
        ctx_filtered = " ".join(c.get('text_content', '') for c in filtered)
        gate_raw = context_has_entity(entity_type, ctx_all) if entity_type != 'none' else None
        gate_filtered = context_has_entity(entity_type, ctx_filtered) if entity_type != 'none' else None

        sims = [c.get('_sim') or 0.0 for c in raw_chunks]
        passing = [s for s in sims if s >= _SIM_THRESHOLD]
        failing = [s for s in sims if s < _SIM_THRESHOLD]

        extracted = extract_for_mode(ctx_filtered, question, mode)

    print(f"  entity_type={entity_type}  mode={mode}  bm25_top={top_score:.1f}")
    print(f"  chunks_raw={len(raw_chunks)}  chunks_filtered={len(filtered)}")
    print(f"  low_confidence={'YES' if top_score < _CONFIDENCE_THRESHOLD else 'NO'}")
    print(f"  sim_scores: {[f'{s:.3f}' for s in sorted(sims, reverse=True)]}")
    print(f"  passing_sim={len(passing)} failing_sim={len(failing)}")
    if entity_type != 'none':
        print(f"  entity_gate(raw_ctx)={gate_raw}  entity_gate(filtered_ctx)={gate_filtered}")

    print(f"\n  RAW CHUNKS (RRF order):")
    for i, c in enumerate(raw_chunks):
        sim = c.get('_sim') or 0.0
        marker = "PASS" if sim >= _SIM_THRESHOLD else "DROP"
        print(f"  {marker} {describe_chunk(c, i)}")

    print(f"\n  FILTERED CHUNKS ({len(filtered)}):")
    for i, c in enumerate(filtered):
        print(f"  {describe_chunk(c, i)}")

    budget = MODE_SENTENCE_BUDGET.get(mode) if 'MODE_SENTENCE_BUDGET' in dir() else None
    with app.app_context():
        from app.services.ai.sentence_extractor import MODE_SENTENCE_BUDGET
        budget = MODE_SENTENCE_BUDGET.get(mode)

    print(f"\n  EXTRACTED (mode={mode}, budget={budget}):")
    print(f"  ctx_len={len(ctx_filtered)} → extracted_len={len(extracted)}")
    print(f"  {extracted[:500]!r}")

    return dict(
        raw=len(raw_chunks), filtered=len(filtered), top_score=top_score,
        entity_type=entity_type, mode=mode,
        gate_filtered=gate_filtered, sims=sims, extracted=extracted,
    )


# ============================================================
# ISSUE 1 — Hans Kohn
# ============================================================
def investigate_issue1():
    print(f"\n{DIVIDER}")
    print("ISSUE 1: 'Siapakah Hans Kohn?' fails; conceptual query succeeds")
    print(DIVIDER)

    q1 = "Siapakah Hans Kohn?"
    q2 = "Nyatakan idea nasionalisme menurut Hans Kohn."

    r1 = run_single_trace(q1, "Issue 1a — Siapakah Hans Kohn?")
    r2 = run_single_trace(q2, "Issue 1b — Nyatakan idea nasionalisme menurut Hans Kohn.")

    print(f"\n  COMPARISON:")
    print(f"  Siapakah: filtered={r1['filtered']}  bm25={r1['top_score']:.1f}  "
          f"low_conf={'YES' if r1['top_score']<_CONFIDENCE_THRESHOLD else 'NO'}  gate={r1['gate_filtered']}")
    print(f"  Nyatakan: filtered={r2['filtered']}  bm25={r2['top_score']:.1f}  "
          f"low_conf={'YES' if r2['top_score']<_CONFIDENCE_THRESHOLD else 'NO'}  gate={r2['gate_filtered']}")

    # Show full text of surviving chunks for Siapakah
    raw, filtered, _ = retrieve_and_filter(q1)
    print(f"\n  FULL TEXT of {len(filtered)} chunk(s) surviving filter for 'Siapakah Hans Kohn?':")
    for i, c in enumerate(filtered):
        print(f"\n  --- chunk {i} t={c.get('topic_id')} pg={c.get('page_number')} idx={c.get('chunk_index')} ---")
        print(f"  {c.get('text_content', '')}")


# ============================================================
# ISSUE 2 — Year 1776
# ============================================================
def investigate_issue2():
    print(f"\n{DIVIDER}")
    print("ISSUE 2: 'pada tahun 1776?' → tidak dinyatakan")
    print(DIVIDER)

    q = "Apakah peristiwa yang berlaku pada tahun 1776?"
    run_single_trace(q, "Issue 2 — pada tahun 1776")

    raw, filtered, _ = retrieve_and_filter(q)
    ctx = " ".join(c.get('text_content', '') for c in filtered)
    ctx_all = " ".join(c.get('text_content', '') for c in raw)

    # Check years present in context
    years_filtered = sorted(set(re.findall(r'\b1[0-9]{3}\b', ctx)))
    years_all = sorted(set(re.findall(r'\b1[0-9]{3}\b', ctx_all)))
    print(f"\n  Years in FILTERED context: {years_filtered}")
    print(f"  Years in RAW context (pre-filter): {years_all}")
    print(f"  '1776' in filtered: {'1776' in ctx}")
    print(f"  '1776' in raw: {'1776' in ctx_all}")

    with app.app_context():
        from app.services.ai.entity_gate import context_has_entity
        print(f"  entity_gate('date', filtered_ctx) = {context_has_entity('date', ctx)}")
        print(f"  entity_gate('date', raw_ctx) = {context_has_entity('date', ctx_all)}")

    # What does entity gate 'date' check for?
    print(f"\n  Checking entity_gate 'date' implementation...")
    with app.app_context():
        import inspect
        from app.services.ai import entity_gate as eg
        print(inspect.getsource(eg.context_has_entity))


# ============================================================
# ISSUE 3 — jus soli consistency
# ============================================================
def investigate_issue3():
    print(f"\n{DIVIDER}")
    print("ISSUE 3: 'Apakah maksud jus soli?' — inconsistency across runs")
    print(DIVIDER)

    q = "Apakah maksud jus soli?"

    print(f"\n  Running 5 retrieval traces to check variability...")
    results = []
    for run in range(5):
        raw, filtered, top_score = retrieve_and_filter(q)
        with app.app_context():
            from app.services.ai.question_classifier import classify_question
            from app.services.ai.sentence_extractor import extract_for_mode
            mode = classify_question(q)
            ctx = " ".join(c.get('text_content', '') for c in filtered)
            extracted = extract_for_mode(ctx, q, mode)

        chunk_ids = [(c.get('topic_id'), c.get('page_number'), c.get('chunk_index')) for c in filtered]
        sims = [c.get('_sim') or 0.0 for c in raw]
        results.append({
            'run': run + 1,
            'filtered': len(filtered),
            'chunk_ids': chunk_ids,
            'jus_ctx': 'jus soli' in ctx.lower(),
            'jus_ext': 'jus soli' in extracted.lower(),
            'top_score': top_score,
            'sims': sims,
        })
        time.sleep(0.1)

    print(f"\n  Run summary:")
    for r in results:
        print(f"  Run {r['run']}: filtered={r['filtered']}  bm25={r['top_score']:.1f}  "
              f"jus_in_ctx={r['jus_ctx']}  jus_in_extracted={r['jus_ext']}")
        print(f"    chunk_ids: {r['chunk_ids']}")

    unique_sets = set(frozenset(r['chunk_ids']) for r in results)
    print(f"\n  Unique retrieval sets: {len(unique_sets)}")
    print(f"  Retrieval {'DETERMINISTIC' if len(unique_sets)==1 else 'NON-DETERMINISTIC'}")
    print(f"  jus_in_ctx across runs: {[r['jus_ctx'] for r in results]}")
    print(f"  jus_in_extracted: {[r['jus_ext'] for r in results]}")

    # Deep dive first run
    raw, filtered, top_score = retrieve_and_filter(q)
    with app.app_context():
        from app.services.ai.question_classifier import classify_question
        from app.services.ai.sentence_extractor import extract_for_mode
        mode = classify_question(q)
        ctx = " ".join(c.get('text_content', '') for c in filtered)
        extracted = extract_for_mode(ctx, q, mode)

    print(f"\n  DEEP DIVE raw chunks:")
    for i, c in enumerate(raw):
        sim = c.get('_sim') or 0.0
        marker = "PASS" if sim >= _SIM_THRESHOLD else "DROP"
        print(f"  {marker} {describe_chunk(c, i)}")

    print(f"\n  EXTRACTED sentences (split):")
    sents = re.split(r'(?<=[.!?])\s+', extracted)
    for i, s in enumerate(sents):
        tag = " <JUS_SOLI>" if 'jus soli' in s.lower() else ""
        print(f"  [{i}]{tag} {s[:180]!r}")

    # Specifically locate the jus soli chunk
    print(f"\n  Searching for 'jus soli' in ALL raw chunks:")
    for i, c in enumerate(raw):
        if 'jus soli' in c.get('text_content', '').lower():
            sim = c.get('_sim') or 0.0
            print(f"  FOUND: {describe_chunk(c, i)}")
            print(f"    sim={sim:.3f} (threshold={_SIM_THRESHOLD}) → {'PASS' if sim>=_SIM_THRESHOLD else 'DROP'}")
            print(f"    FULL TEXT: {c.get('text_content', '')[:600]}")


if __name__ == '__main__':
    investigate_issue1()
    investigate_issue2()
    investigate_issue3()

    print(f"\n{DIVIDER}")
    print("DIAGNOSTIC COMPLETE")
    print(DIVIDER)
