"""
Comprehensive quiz quality and diversity diagnostic.

Run: cd backend && PYTHONPATH=. ./venv/bin/python scripts/diag_question_quality.py
"""
import re
from collections import Counter, defaultdict
from itertools import combinations

from app import create_app
from app.extensions import db


# ─── helpers ──────────────────────────────────────────────────────────────────

def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


# BM stopwords for meaningful-token extraction
_STOP = {
    'yang', 'dan', 'untuk', 'pada', 'dengan', 'dari', 'tidak', 'ini', 'itu',
    'adalah', 'akan', 'telah', 'dalam', 'oleh', 'kepada', 'apakah', 'siapa',
    'bilakah', 'di', 'ke', 'se', 'antara', 'atau', 'juga', 'bagi', 'satu',
    'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'lapan', 'sembilan',
    'sepuluh', 'merupakan', 'tentang', 'lebih', 'paling', 'sangat',
    'mana', 'manakal', 'apabila', 'bagaimana', 'mengapa', 'kenapa',
}

def key_tokens(text: str) -> set:
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return {w for w in words if w not in _STOP}


# ─── cognitive-level classifier ───────────────────────────────────────────────

_RE_RECALL = re.compile(
    r'\b(?:siapa(?:kah)?|bila(?:kah)?|tahun\s+berapa|di\s+mana(?:kah)?'
    r'|apakah\s+nama|berapa\b|pada\s+tahun|pada\s+abad'
    r'|apakah\s+(?:nama|gelaran|jawatan|pangkat|gelaran|tarikh|tahun|hari))'
    r'\b',
    re.IGNORECASE,
)

_RE_CAUSE_EFFECT = re.compile(
    r'\b(?:mengapa|kenapa|apakah\s+sebab|apakah\s+faktor'
    r'|apakah\s+kesan|apakah\s+akibat|apakah\s+impak'
    r'|apakah\s+pengaruh|mengakibatkan|menyebabkan)'
    r'\b',
    re.IGNORECASE,
)

_RE_PURPOSE_SIGNIFICANCE = re.compile(
    r'\b(?:apakah\s+tujuan|apakah\s+matlamat|apakah\s+kepentingan'
    r'|apakah\s+peranan|apakah\s+sumbangan|apakah\s+fungsi)'
    r'\b',
    re.IGNORECASE,
)

_RE_COMPARISON = re.compile(
    r'\b(?:bandingkan|bezakan|perbezaan\s+antara|persamaan\s+antara'
    r'|berbeza|berbanding)\b',
    re.IGNORECASE,
)

_RE_HOTS = re.compile(
    r'\b(?:nilaikan|analisis(?:kan)?|justifika(?:si|sikan)'
    r'|buktikan|beri\s+pendapat|sejauh\s+mana|mengapa\s+penting'
    r'|huraikan\s+kepentingan|jelaskan\s+kesan)\b',
    re.IGNORECASE,
)

_RE_DEFINITION = re.compile(
    r'\b(?:apakah\s+(?:yang\s+dimaksudkan|maksud|definisi|konsep|sistem|dasar|prinsip)'
    r'|merujuk\s+kepada|dikenali\s+sebagai|bermaksud)\b',
    re.IGNORECASE,
)

_RE_DATE_YEAR = re.compile(
    r'\b(?:tahun\s+berapa|pada\s+tahun|pada\s+abad|tarikh|bilakah|(?:19|20)\d\d)\b',
    re.IGNORECASE,
)

def classify_cognitive(stem: str) -> str:
    if _RE_COMPARISON.search(stem):   return 'comparison'
    if _RE_HOTS.search(stem):         return 'hots'
    if _RE_CAUSE_EFFECT.search(stem): return 'cause_effect'
    if _RE_PURPOSE_SIGNIFICANCE.search(stem): return 'purpose_significance'
    if _RE_DEFINITION.search(stem):   return 'definition'
    if _RE_DATE_YEAR.search(stem):    return 'date_year'
    if _RE_RECALL.search(stem):       return 'factual_recall'
    return 'applied'

COG_LABEL = {
    'date_year':           'Date/Year recall',
    'factual_recall':      'Factual recall (who/where)',
    'definition':          'Definition/concept',
    'cause_effect':        'Cause & effect',
    'purpose_significance':'Purpose/significance',
    'comparison':          'Comparison/contrast',
    'hots':                'HOTS/evaluation',
    'applied':             'Applied/other',
}


# ─── distractor quality indicators ────────────────────────────────────────────

_TRIVIAL_OPT = {
    'semua di atas', 'tiada yang betul', 'tiada jawapan',
    'all of the above', 'none of the above',
    'semua jawapan di atas', 'kesemua di atas',
}

def distractor_flags(options: list, correct_index: int) -> list:
    flags = []
    distractors = [o.strip().lower() for i, o in enumerate(options) if i != correct_index]
    correct = options[correct_index].strip().lower()

    # trivial distractors
    for d in distractors:
        if d in _TRIVIAL_OPT:
            flags.append('trivial_distractor')
            break

    # number-only distractors (date-swap risk)
    if all(re.fullmatch(r'[\d\s]+', d) for d in distractors):
        flags.append('all_numeric_distractors')

    # all distractors from same token pool → over-similar
    # (handled by Jaccard in validator; flag here for reporting)
    for d1, d2 in combinations(distractors, 2):
        j = jaccard(d1, d2)
        if j > 0.65:
            flags.append('near_duplicate_distractors')
            break

    # single-word distractors (too brief to assess plausibility)
    if all(len(d.split()) == 1 for d in distractors):
        flags.append('single_word_distractors')

    return flags


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    app = create_app()
    with app.app_context():
        from app.models.attempt_question import AttemptQuestion
        from app.models.quiz_attempt import QuizAttempt
        from app.models.quiz import Quiz

        rows = (
            db.session.query(
                AttemptQuestion.attempt_question_id,
                AttemptQuestion.stem,
                AttemptQuestion.options,
                AttemptQuestion.correct_index,
                AttemptQuestion.explanation,
                AttemptQuestion.order_index,
                QuizAttempt.attempt_id,
                QuizAttempt.quiz_id,
                Quiz.form_level,
                Quiz.chapter_id,
            )
            .join(QuizAttempt, AttemptQuestion.attempt_id == QuizAttempt.attempt_id)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.quiz_id)
            .all()
        )

        if not rows:
            print("No attempt_question rows found.")
            return

        total = len(rows)
        W = 68

        print('\n' + '='*W)
        print(f'  QUIZ QUALITY & DIVERSITY DIAGNOSTIC — {total} questions')
        print('='*W)

        # ── 1. Group by quiz and attempt ────────────────────────────────
        by_quiz   = defaultdict(list)   # quiz_id → list of rows
        by_attempt = defaultdict(list)  # attempt_id → list of rows
        for r in rows:
            by_quiz[r.quiz_id].append(r)
            by_attempt[r.attempt_id].append(r)

        # ── 2. Cognitive level distribution ─────────────────────────────
        cog_counter = Counter(classify_cognitive(r.stem) for r in rows)
        print('\n[1] COGNITIVE LEVEL DISTRIBUTION')
        print(f"    {'Category':<30} {'N':>4}  {'%':>6}  Bar")
        print(f"    {'-'*30} {'-'*4}  {'-'*6}  ---")
        for ctype, label in COG_LABEL.items():
            n = cog_counter.get(ctype, 0)
            pct = n / total * 100
            bar = '█' * int(pct / 3)
            print(f"    {label:<30} {n:>4}  {pct:5.1f}%  {bar}")

        lo_order = (cog_counter.get('date_year', 0)
                    + cog_counter.get('factual_recall', 0)
                    + cog_counter.get('definition', 0))
        hi_order = (cog_counter.get('cause_effect', 0)
                    + cog_counter.get('purpose_significance', 0)
                    + cog_counter.get('comparison', 0)
                    + cog_counter.get('hots', 0))
        print(f"\n    LOW-ORDER  (recall+date+definition): {lo_order}/{total} "
              f"= {lo_order/total*100:.0f}%")
        print(f"    HIGHER-ORDER (cause+purpose+compare+HOTS): {hi_order}/{total} "
              f"= {hi_order/total*100:.0f}%")
        spm_lo = 55  # approximate SPM Sejarah low-order %
        spm_hi = 45
        print(f"    SPM Sejarah target: ~{spm_lo}% low-order / ~{spm_hi}% higher-order")

        # ── 3. Distractor quality ────────────────────────────────────────
        print('\n[2] DISTRACTOR QUALITY FLAGS')
        dist_flag_counter: Counter = Counter()
        flagged_qs = []
        for r in rows:
            flags = distractor_flags(r.options, r.correct_index)
            for f in flags:
                dist_flag_counter[f] += 1
            if flags:
                flagged_qs.append((r, flags))

        flag_labels = {
            'all_numeric_distractors':    'All-numeric options (date swaps only)',
            'single_word_distractors':    'Single-word distractors (too brief)',
            'trivial_distractor':         'Trivial option ("semua di atas" etc.)',
            'near_duplicate_distractors': 'Near-duplicate distractor pair (Jaccard>0.65)',
        }
        for fkey, flabel in flag_labels.items():
            n = dist_flag_counter.get(fkey, 0)
            pct = n / total * 100
            print(f"    {flabel:<44} {n:>4} ({pct:.1f}%)")

        # Show 3 flagged examples
        if flagged_qs:
            print("\n    Sample flagged questions:")
            for r, flags in flagged_qs[:3]:
                correct_opt = r.options[r.correct_index]
                distractors = [o for i, o in enumerate(r.options) if i != r.correct_index]
                print(f"      [{', '.join(flags)}]")
                print(f"      Q: {r.stem[:90]}")
                print(f"      Correct: {correct_opt}")
                print(f"      Distractors: {' | '.join(distractors)}")
                print()

        # ── 4. Cross-attempt similarity (same quiz, different attempts) ──
        print('\n[3] CROSS-ATTEMPT SIMILARITY (same quiz)')
        NEAR_DUP_THRESHOLD = 0.50  # matches generator's own dedup threshold

        cross_pairs_total   = 0
        near_dup_total      = 0
        exact_dup_total     = 0
        quiz_stats          = []

        for quiz_id, qrows in by_quiz.items():
            # Group by attempt
            attempt_groups: dict = defaultdict(list)
            for r in qrows:
                attempt_groups[r.attempt_id].append(r)

            attempt_ids = sorted(attempt_groups.keys())
            if len(attempt_ids) < 2:
                continue

            # Compare all (attempt_i, attempt_j) pairs
            quiz_near_dups = 0
            quiz_exact_dups = 0
            quiz_pairs = 0
            sample_near_dups = []

            for aid1, aid2 in combinations(attempt_ids, 2):
                stems1 = [r.stem for r in attempt_groups[aid1]]
                stems2 = [r.stem for r in attempt_groups[aid2]]
                for s1 in stems1:
                    for s2 in stems2:
                        quiz_pairs += 1
                        j = jaccard(s1, s2)
                        if j >= 0.90:
                            exact_dup_total += 1
                            quiz_exact_dups += 1
                        elif j >= NEAR_DUP_THRESHOLD:
                            near_dup_total += 1
                            quiz_near_dups += 1
                            if len(sample_near_dups) < 2:
                                sample_near_dups.append((j, s1, s2))

            cross_pairs_total += quiz_pairs
            form_level = qrows[0].form_level
            chapter_id = qrows[0].chapter_id
            n_attempts = len(attempt_ids)
            n_questions = len(qrows)
            quiz_stats.append((
                form_level, chapter_id, n_attempts, n_questions,
                quiz_exact_dups, quiz_near_dups, quiz_pairs, sample_near_dups,
            ))

        if quiz_stats:
            print(f"\n    {'Chapter':<12} {'Attempts':>8} {'Q-pairs':>8} "
                  f"{'ExactDup':>9} {'NearDup':>8} {'DupRate':>8}")
            print(f"    {'-'*12} {'-'*8} {'-'*8} {'-'*9} {'-'*8} {'-'*8}")
            total_dup_rate_pct = 0.0
            for (fl, ch, n_att, n_q, exact, near, pairs, _) in sorted(quiz_stats):
                dup_rate = (exact + near) / pairs * 100 if pairs else 0
                total_dup_rate_pct += dup_rate
                print(f"    F{fl}-Bab{ch:<8} {n_att:>8} {pairs:>8} "
                      f"{exact:>9} {near:>8} {dup_rate:>7.1f}%")

            print(f"\n    Total cross-attempt question pairs: {cross_pairs_total}")
            print(f"    Exact duplicates (Jaccard ≥ 0.90):  {exact_dup_total}")
            print(f"    Near-duplicates (Jaccard ≥ 0.50):   {near_dup_total}")
            if cross_pairs_total:
                overall_dup = (exact_dup_total + near_dup_total) / cross_pairs_total * 100
                print(f"    Overall duplicate rate:             {overall_dup:.1f}%")

            # Print sample near-duplicates
            print("\n    Sample near-duplicate pairs:")
            shown = 0
            for (fl, ch, n_att, n_q, exact, near, pairs, samples) in sorted(quiz_stats):
                for j, s1, s2 in samples:
                    if shown >= 4:
                        break
                    print(f"      [Jaccard={j:.2f} F{fl}-Bab{ch}]")
                    print(f"      A: {s1[:85]}")
                    print(f"      B: {s2[:85]}")
                    print()
                    shown += 1
                if shown >= 4:
                    break
        else:
            print("    No quiz has multiple attempts — cannot measure cross-attempt similarity.")
            print("    (Need at least 2 completed attempts on the same quiz.)")

        # ── 5. Within-attempt angle analysis ────────────────────────────
        print('\n[4] QUESTION ANGLE (TOPIC FOCUS) — order_index mapping')
        print('    The generator cycles through 10 angles by order_index % 10.')
        ANGLES = [
            "definisi konsep utama",
            "sebab atau punca peristiwa",
            "tarikh atau tempoh masa",
            "tokoh atau pemimpin",
            "kesan atau akibat peristiwa",
            "perjanjian / dokumen",
            "lokasi atau tempat",
            "ciri-ciri atau kandungan utama",
            "perbandingan antara dua perkara",
            "fakta spesifik tentang peristiwa/tokoh",
        ]
        angle_counter = Counter()
        for r in rows:
            angle_idx = (r.order_index - 1) % 10
            cog = classify_cognitive(r.stem)
            angle_counter[ANGLES[angle_idx]] += 1

        print(f"\n    {'Angle':<42} {'N':>4}  {'Cog dominance'}")
        print(f"    {'-'*42} {'-'*4}  {'-'*15}")

        # For each angle, find the actual cognitive distribution
        angle_cog: dict = defaultdict(Counter)
        for r in rows:
            ai = (r.order_index - 1) % 10
            angle_cog[ANGLES[ai]][classify_cognitive(r.stem)] += 1

        for ai, angle in enumerate(ANGLES):
            n = angle_counter.get(angle, 0)
            cog_dist = angle_cog.get(angle, Counter())
            if cog_dist:
                dom = cog_dist.most_common(1)[0][0]
                dom_pct = cog_dist.most_common(1)[0][1] / n * 100 if n else 0
                dom_label = COG_LABEL.get(dom, dom)
                print(f"    {angle:<42} {n:>4}  {dom_label} ({dom_pct:.0f}%)")
            else:
                print(f"    {angle:<42} {n:>4}  —")

        # ── 6. Sample questions for qualitative review ───────────────────
        print('\n[5] SAMPLE QUESTIONS (qualitative review)')
        by_cog: dict = defaultdict(list)
        for r in rows:
            by_cog[classify_cognitive(r.stem)].append(r)

        categories_to_show = [
            'date_year', 'factual_recall', 'definition',
            'cause_effect', 'purpose_significance', 'applied',
        ]
        for cat in categories_to_show:
            qs = by_cog.get(cat, [])
            if not qs:
                continue
            sample = qs[:2]
            print(f"\n  --- {COG_LABEL[cat]} ({len(qs)} total) ---")
            for r in sample:
                correct_opt = r.options[r.correct_index]
                distractors = [o for i, o in enumerate(r.options) if i != r.correct_index]
                print(f"  Q: {r.stem}")
                print(f"  Correct: {correct_opt}")
                print(f"  Distractors: {' | '.join(distractors)}")
                if r.explanation:
                    print(f"  Explanation: {r.explanation[:120]}")
                print()

        # ── 7. Within-attempt topic repetition ──────────────────────────
        print('\n[6] WITHIN-ATTEMPT TOPIC REPETITION (questions sharing key tokens)')
        OVERLAP_THRESHOLD = 0.35  # lower than cross-attempt, more strict within
        within_dup_count = 0
        total_within_pairs = 0
        for aid, qs in by_attempt.items():
            for i, q1 in enumerate(qs):
                for j, q2 in enumerate(qs):
                    if j <= i:
                        continue
                    total_within_pairs += 1
                    k1, k2 = key_tokens(q1.stem), key_tokens(q2.stem)
                    union = k1 | k2
                    if union:
                        overlap = len(k1 & k2) / len(union)
                        if overlap > OVERLAP_THRESHOLD:
                            within_dup_count += 1

        if total_within_pairs:
            within_pct = within_dup_count / total_within_pairs * 100
            print(f"    Within-attempt overlapping pairs (key-token Jaccard >{OVERLAP_THRESHOLD}): "
                  f"{within_dup_count}/{total_within_pairs} = {within_pct:.1f}%")
        else:
            print("    (insufficient data)")

        # ── 8. Architecture root-cause summary ──────────────────────────
        print('\n' + '='*W)
        print('  ROOT-CAUSE SUMMARY')
        print('='*W)

        total_quizzes  = len(by_quiz)
        multi_attempt  = sum(1 for qid, qrows in by_quiz.items()
                            if len({r.attempt_id for r in qrows}) > 1)
        print(f"""
  ARCHITECTURAL CONSTRAINTS (from code analysis):
  ─────────────────────────────────────────────────
  A1. Fixed angle order: pick_angle(order_index % 10) — every 10-question
      quiz has an identical angle sequence. Q1=definition, Q2=cause, etc.
      Students who retake see the same angle pattern every time.

  A2. Same context every attempt: _stratified_context() samples the same
      pages for every attempt on the same chapter. The LLM sees identical
      source text → similar outputs.

  A3. No cross-attempt deduplication: _is_duplicate() compares only within
      the current generation run. Previous attempts are never consulted.

  A4. Prompt anchors factual recall: all 10 angles except "perbandingan"
      are phrased as factual targets (name, date, place, fact). The prompt
      then asks for "SATU fakta spesifik" — this biases the LLM toward
      simple recall regardless of angle.

  A5. Temperature 0.65 with identical context → limited output variance.
      The LLM will converge toward the most likely factual answers in text.

  DATA:
  ─────
  {total} questions from {total_quizzes} quiz(zes), {len(by_attempt)} attempt(s).
  Quizzes with multiple attempts: {multi_attempt}
""")
        print('='*W)
        print()


if __name__ == '__main__':
    main()
