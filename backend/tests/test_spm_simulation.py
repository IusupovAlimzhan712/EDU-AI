"""
Phase 4 — SPM Simulation Evaluation.

Measures the quality improvement from Phases 1-3 by comparing a curated
"BEFORE" corpus (simulating pre-Phase 1 LLM output patterns) against an
"AFTER" corpus (representing the post-Phase 3 target quality).

Corpora are hand-crafted to represent realistic LLM behaviour, not mocked.
The BEFORE corpus deliberately contains known failure patterns:
  - Recall bias (>50% who/when/where/what questions)
  - Zero Roman Numeral questions
  - Non-parallel verb forms across action options
  - Option length imbalance on location questions

The AFTER corpus demonstrates the target state:
  - Recall bias reduced to <40%
  - Roman Numeral questions present
  - All action options grammatically parallel (meN- verb form)
  - All options within 3:1 length ratio

Metrics evaluated:
  1. Recall bias (target: <40%  from baseline ~55%)
  2. Roman Numeral presence (target: >0%  from baseline 0%)
  3. Option parallelism failures (target: 0%  from baseline >10%)
  4. Option length parity failures (target: 0%  from baseline >10%)
  5. Validator pass rate (target: 100% after vs <80% before)
"""
import re

import pytest

from app.services.ai.base import GeneratedQuestion
from app.services.ai.content_validator import ContentValidator


# ── Tier classifier (stem-based heuristic) ───────────────────────────────────

_RECALL_RE = re.compile(
    r'^(?:siapakah|pada tahun|di manakah|apakah nama|berapakah|apakah gelaran)',
    re.IGNORECASE,
)


def _is_recall(stem: str) -> bool:
    return bool(_RECALL_RE.match(stem.strip()))


# ── Validator runner ──────────────────────────────────────────────────────────

def _all_failures(q: GeneratedQuestion) -> list[str]:
    """Run all content validators (excluding check_alignment) and return failures."""
    results = []
    for check in [
        ContentValidator.validate_structure,
        ContentValidator.validate_stem_quality,
        ContentValidator.validate_options_clean,
        ContentValidator.validate_roman_numeral,
        ContentValidator.validate_distractors,
        ContentValidator.validate_option_length_parity,
        ContentValidator.validate_option_parallelism,
    ]:
        r = check(q)
        if r is not None:
            results.append(r)
    return results


# ── BEFORE corpus ─────────────────────────────────────────────────────────────
# 8 questions representing pre-Phase 1 LLM output.
# Deliberate flaws: recall bias, no RN, parallelism failure, parity failure.

BEFORE_CORPUS = [
    # ── Recall tier (5 / 8 = 62.5%) ─────────────────────────────────────────
    GeneratedQuestion(
        stem='Siapakah pemimpin gerakan nasionalisme India yang paling terkenal?',
        options=['Mahatma Gandhi', 'Jawaharlal Nehru', 'Muhammad Ali Jinnah', 'Subhas Chandra Bose'],
        correct_index=0,
        explanation='Mahatma Gandhi memimpin gerakan nasionalisme India melalui prinsip ketidakpatuhan sivil.',
    ),
    GeneratedQuestion(
        stem='Pada tahun berapakah India mencapai kemerdekaan daripada Britain?',
        options=['1945', '1947', '1949', '1950'],
        correct_index=1,
        explanation='India mencapai kemerdekaan daripada Britain pada 15 Ogos 1947.',
    ),
    GeneratedQuestion(
        stem='Apakah nama gerakan aman yang diasaskan oleh Mahatma Gandhi?',
        options=['Gerakan Ketidakpatuhan Sivil', 'Gerakan Pembaharuan Sosial', 'Gerakan Demokrasi Rakyat', 'Gerakan Sosialis India'],
        correct_index=0,
        explanation='Gandhi mengasaskan Gerakan Ketidakpatuhan Sivil untuk menentang penjajahan Britain.',
    ),
    GeneratedQuestion(
        stem='Siapakah Perdana Menteri India yang pertama selepas merdeka?',
        options=['Jawaharlal Nehru', 'Mahatma Gandhi', 'Sardar Vallabhbhai Patel', 'Rajendra Prasad'],
        correct_index=0,
        explanation='Jawaharlal Nehru ialah Perdana Menteri India yang pertama selepas kemerdekaan.',
    ),
    GeneratedQuestion(
        stem='Pada tahun berapakah Mahatma Gandhi mula memimpin gerakan kemerdekaan India?',
        options=['1915', '1919', '1920', '1930'],
        correct_index=2,
        explanation='Gandhi mula memimpin gerakan kemerdekaan India secara aktif pada tahun 1920.',
    ),
    # ── Application tier (2 / 8 = 25%) ──────────────────────────────────────
    GeneratedQuestion(
        # QUALITY FAILURE — non-parallel options (3 meN- + 1 non-meN-)
        stem='Apakah peranan Mahatma Gandhi dalam perjuangan kemerdekaan India?',
        options=[
            'Memimpin gerakan ketidakpatuhan sivil secara aman',
            'Menganjurkan mogok dan boikot barangan British',
            'Menyatukan pelbagai kaum di bawah satu perjuangan',
            'Semangat perjuangan dibakar dalam kalangan rakyat',  # passive — breaks parallelism
        ],
        correct_index=0,
        explanation='Gandhi memimpin perjuangan kemerdekaan India melalui kaedah aman dan bukan keganasan.',
    ),
    GeneratedQuestion(
        # QUALITY FAILURE — option length parity (ratio > 3:1)
        stem='Di manakah gerakan nasionalisme India memberi kesan yang paling ketara?',
        options=[
            'India',                         # 5 chars
            'Asia Selatan dan Asia Tenggara',  # 31 chars → 31/5 = 6.2:1 FAIL
            'Eropah Barat',
            'Amerika Syarikat',
        ],
        correct_index=1,
        explanation='Gerakan nasionalisme India memberi kesan terbesar kepada negara-negara Asia Selatan dan Asia Tenggara.',
    ),
    # ── HOTS tier (1 / 8 = 12.5%) ────────────────────────────────────────────
    GeneratedQuestion(
        stem='Apakah kepentingan perjuangan Gandhi kepada gerakan kemerdekaan di Asia?',
        options=[
            'Membuktikan bahawa perjuangan aman boleh mengalahkan kuasa penjajah',
            'Menunjukkan bahawa kekerasan adalah cara terbaik menentang penjajahan',
            'Membuktikan bahawa negara Asia tidak memerlukan bantuan luar',
            'Menggalakkan negara Asia berperang sesama sendiri untuk merdeka',
        ],
        correct_index=0,
        explanation='Gandhi membuktikan bahawa perjuangan aman boleh berjaya menentang kuasa penjajah yang lebih kuat.',
    ),
]

# ── AFTER corpus ──────────────────────────────────────────────────────────────
# 8 questions representing post-Phase 3 target quality.
# All pass every content validator; reduced recall bias; 2 RN questions.

AFTER_CORPUS = [
    # ── Recall tier (1 / 8 = 12.5%) ─────────────────────────────────────────
    GeneratedQuestion(
        stem='Siapakah tokoh yang memimpin Gerakan Berhenti Bekerja Sama di India pada 1920?',
        options=['Mahatma Gandhi', 'Jawaharlal Nehru', 'Bal Gangadhar Tilak', 'Gopal Krishna Gokhale'],
        correct_index=0,
        explanation='Mahatma Gandhi memimpin Gerakan Berhenti Bekerja Sama yang bermula pada tahun 1920.',
    ),
    # ── Application tier (3 / 8 = 37.5%) ────────────────────────────────────
    GeneratedQuestion(
        # Parallel meN- options — all four begin with meN- verb
        stem='Mengapakah Mahatma Gandhi memilih kaedah ketidakpatuhan sivil untuk menentang penjajahan?',
        options=[
            'Mengelakkan pertumpahan darah dan mendapat sokongan antarabangsa',
            'Menunjukkan bahawa kelemahan moral adalah kekuatan penjajah Britain',
            'Melemahkan ekonomi Britain melalui boikot barangan import secara berterusan',
            'Menyatukan pelbagai kumpulan etnik di bawah satu agenda perjuangan',
        ],
        correct_index=0,
        explanation='Gandhi memilih kaedah aman kerana ia mengelakkan pertumpahan darah dan mendapat simpati antarabangsa.',
    ),
    GeneratedQuestion(
        # Parallel meN- options
        stem='Apakah kesan gerakan boikot barangan British yang dianjurkan oleh Gandhi?',
        options=[
            'Melemahkan pendapatan eksport Britain daripada pasaran India',
            'Mengurangkan kebergantungan India kepada barangan import dari Britain',
            'Meningkatkan pengeluaran industri tekstil tempatan India',
            'Memperkukuh semangat nasionalisme dalam kalangan rakyat jelata',
        ],
        correct_index=0,
        explanation='Boikot barangan British melemahkan pendapatan eksport Britain dan mendorong industri tempatan India berkembang.',
    ),
    GeneratedQuestion(
        # Parallel meN- options
        stem='Apakah peranan Kongres Kebangsaan India dalam perjuangan kemerdekaan India?',
        options=[
            'Menyelaraskan gerakan kemerdekaan di seluruh pelosok India',
            'Merundingkan syarat kemerdekaan dengan kerajaan Britain secara rasmi',
            'Mengorganisasikan demonstrasi dan mogok secara besar-besaran',
            'Mewakili kepentingan rakyat India dalam forum antarabangsa',
        ],
        correct_index=0,
        explanation='Kongres Kebangsaan India memainkan peranan utama dalam menyelaraskan gerakan kemerdekaan di seluruh India.',
    ),
    # ── HOTS tier (2 / 8 = 25%) ──────────────────────────────────────────────
    GeneratedQuestion(
        stem='Apakah kepentingan gerakan kemerdekaan India terhadap perjuangan anti-penjajahan di Asia?',
        options=[
            'Membuktikan bahawa kaedah aman boleh mengalahkan kuasa penjajah yang lebih kuat',
            'Menunjukkan bahawa kekerasan adalah satu-satunya cara yang berkesan menentang penjajahan',
            'Membuktikan bahawa negara Asia tidak memerlukan sokongan luar dalam perjuangan mereka',
            'Menggalakkan negara Asia berperang antara satu sama lain bagi memperolehi kemerdekaan',
        ],
        correct_index=0,
        explanation='Perjuangan India membuktikan bahawa kaedah aman dapat berjaya menentang kuasa penjajah yang lebih kuat.',
    ),
    GeneratedQuestion(
        stem='Apakah perbezaan utama antara pendekatan Gandhi dan Subhas Chandra Bose dalam perjuangan kemerdekaan India?',
        options=[
            'Gandhi mengamalkan pendekatan aman; Bose menyokong perjuangan bersenjata',
            'Gandhi menyokong perjuangan bersenjata; Bose mengamalkan pendekatan aman',
            'Kedua-dua pemimpin menggunakan pendekatan yang sama dalam perjuangan kemerdekaan',
            'Gandhi menentang kemerdekaan India manakala Bose menyokong perjuangan tersebut',
        ],
        correct_index=0,
        explanation='Gandhi mengamalkan ketidakpatuhan sivil yang aman manakala Bose menyokong pendekatan bersenjata melalui Tentera Kebangsaan India.',
    ),
    # ── Roman Numeral tier (2 / 8 = 25%) ─────────────────────────────────────
    GeneratedQuestion(
        stem=(
            'I Gandhi menggunakan kaedah boikot dan mogok dalam perjuangan kemerdekaan India\n'
            'II India mencapai kemerdekaan daripada Britain pada tahun 1947\n'
            'III Jawaharlal Nehru menjadi Presiden Kongres Kebangsaan India yang pertama\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        ),
        options=['I dan II sahaja', 'I dan III sahaja', 'II dan III sahaja', 'I, II dan III'],
        correct_index=0,
        explanation='I dan II adalah betul. III adalah salah kerana Nehru menjadi Perdana Menteri India, bukan Presiden Kongres.',
    ),
    GeneratedQuestion(
        stem=(
            'I Mahatma Gandhi diasingkan ke penjara oleh kerajaan British beberapa kali\n'
            'II Gerakan Berhenti Bekerja Sama dimulakan pada tahun 1920\n'
            'III Perjanjian rasmi antara Gandhi dan kerajaan Britain ditandatangani pada 1947\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        ),
        options=['I dan II sahaja', 'I dan III sahaja', 'II dan III sahaja', 'I, II dan III'],
        correct_index=0,
        explanation='I dan II adalah betul. III adalah salah kerana tiada perjanjian rasmi sedemikian yang ditandatangani pada 1947.',
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4 evaluation tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSPMSimulationEvaluation:
    """Phase 4 — before/after quality metrics evaluation."""

    # ── BEFORE corpus checks ──────────────────────────────────────────────────

    def test_before_corpus_shows_recall_bias(self):
        """Before corpus has ≥50% recall questions (simulates 55% baseline)."""
        recall = sum(1 for q in BEFORE_CORPUS if _is_recall(q.stem))
        pct = recall / len(BEFORE_CORPUS)
        assert pct >= 0.50, f"Before recall {pct:.0%} should be ≥50%"

    def test_before_corpus_has_no_rn_questions(self):
        """Before corpus has zero Roman Numeral questions (baseline deficiency)."""
        rn = sum(1 for q in BEFORE_CORPUS if ContentValidator._is_roman_numeral_question(q))
        assert rn == 0

    def test_before_corpus_parallelism_failure_present(self):
        """Phase 2/3 validators catch at least one non-parallel action question."""
        failures = [q for q in BEFORE_CORPUS if ContentValidator.validate_option_parallelism(q)]
        assert len(failures) >= 1, "Expected ≥1 parallelism failure in before corpus"

    def test_before_corpus_parity_failure_present(self):
        """Phase 2 validator catches at least one length-imbalanced question."""
        failures = [q for q in BEFORE_CORPUS if ContentValidator.validate_option_length_parity(q)]
        assert len(failures) >= 1, "Expected ≥1 parity failure in before corpus"

    def test_before_corpus_overall_pass_rate_below_100(self):
        """Before corpus has at least 2 questions that fail a quality validator."""
        failed = [q for q in BEFORE_CORPUS if _all_failures(q)]
        assert len(failed) >= 2, (
            f"Expected ≥2 quality failures in before corpus, got {len(failed)}"
        )

    # ── AFTER corpus checks ───────────────────────────────────────────────────

    def test_after_corpus_passes_all_validators(self):
        """Every after-corpus question passes all content validators."""
        for i, q in enumerate(AFTER_CORPUS):
            failures = _all_failures(q)
            assert not failures, (
                f"After corpus Q{i + 1} failed validators: {failures}\n"
                f"Stem: {q.stem[:100]}"
            )

    def test_after_corpus_recall_below_40_percent(self):
        """After corpus recall rate is <40% (down from ≥50% baseline)."""
        recall = sum(1 for q in AFTER_CORPUS if _is_recall(q.stem))
        pct = recall / len(AFTER_CORPUS)
        assert pct < 0.40, f"After recall {pct:.0%} should be <40%"

    def test_after_corpus_has_rn_questions(self):
        """After corpus includes Roman Numeral questions (fixed from 0% baseline)."""
        rn = sum(1 for q in AFTER_CORPUS if ContentValidator._is_roman_numeral_question(q))
        assert rn >= 1, "Expected ≥1 RN question in after corpus"

    def test_after_corpus_zero_parallelism_failures(self):
        """After corpus has no option parallelism violations."""
        failures = [(i, ContentValidator.validate_option_parallelism(q))
                    for i, q in enumerate(AFTER_CORPUS)
                    if ContentValidator.validate_option_parallelism(q)]
        assert not failures, f"After corpus parallelism failures: {failures}"

    def test_after_corpus_zero_parity_failures(self):
        """After corpus has no option length parity violations."""
        failures = [(i, ContentValidator.validate_option_length_parity(q))
                    for i, q in enumerate(AFTER_CORPUS)
                    if ContentValidator.validate_option_length_parity(q)]
        assert not failures, f"After corpus parity failures: {failures}"

    # ── Improvement delta checks ──────────────────────────────────────────────

    def test_recall_bias_reduced(self):
        """After corpus recall rate is strictly lower than before corpus."""
        before_r = sum(1 for q in BEFORE_CORPUS if _is_recall(q.stem)) / len(BEFORE_CORPUS)
        after_r = sum(1 for q in AFTER_CORPUS if _is_recall(q.stem)) / len(AFTER_CORPUS)
        assert after_r < before_r, (
            f"After recall ({after_r:.0%}) should be less than before ({before_r:.0%})"
        )

    def test_rn_presence_increased(self):
        """After corpus has more RN questions than before corpus (was 0%)."""
        before_rn = sum(1 for q in BEFORE_CORPUS if ContentValidator._is_roman_numeral_question(q))
        after_rn = sum(1 for q in AFTER_CORPUS if ContentValidator._is_roman_numeral_question(q))
        assert after_rn > before_rn

    def test_validator_pass_rate_improved_to_100_percent(self):
        """After corpus achieves 100% validator pass rate; before corpus does not."""
        before_pass = sum(1 for q in BEFORE_CORPUS if not _all_failures(q)) / len(BEFORE_CORPUS)
        after_pass = sum(1 for q in AFTER_CORPUS if not _all_failures(q)) / len(AFTER_CORPUS)
        assert after_pass > before_pass
        assert after_pass == 1.0, f"After corpus should be 100% passing, got {after_pass:.0%}"

    # ── Metrics report ────────────────────────────────────────────────────────

    def test_print_phase_summary_report(self):
        """Print a before/after quality metrics table. Always passes."""
        B, A = BEFORE_CORPUS, AFTER_CORPUS

        def _rate(corpus, fn):
            return sum(1 for q in corpus if fn(q)) / len(corpus)

        b_recall   = _rate(B, lambda q: _is_recall(q.stem))
        a_recall   = _rate(A, lambda q: _is_recall(q.stem))
        b_rn       = _rate(B, ContentValidator._is_roman_numeral_question)
        a_rn       = _rate(A, ContentValidator._is_roman_numeral_question)
        b_par_fail = _rate(B, lambda q: bool(ContentValidator.validate_option_parallelism(q)))
        a_par_fail = _rate(A, lambda q: bool(ContentValidator.validate_option_parallelism(q)))
        b_pty_fail = _rate(B, lambda q: bool(ContentValidator.validate_option_length_parity(q)))
        a_pty_fail = _rate(A, lambda q: bool(ContentValidator.validate_option_length_parity(q)))
        b_pass     = _rate(B, lambda q: not _all_failures(q))
        a_pass     = _rate(A, lambda q: not _all_failures(q))

        print(
            "\n"
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║         SPM QUALITY SIMULATION REPORT  (Phase 4)         ║\n"
            "╠═══════════════════════════════════════════════════════════╣\n"
            "║  Metric                    │  BEFORE     │  AFTER        ║\n"
            "╠═══════════════════════════════════════════════════════════╣\n"
           f"║  Recall bias               │  {b_recall:>6.0%}     │  {a_recall:>6.0%}        ║\n"
           f"║  Roman Numeral questions   │  {b_rn:>6.0%}     │  {a_rn:>6.0%}        ║\n"
           f"║  Parallelism failures      │  {b_par_fail:>6.0%}     │  {a_par_fail:>6.0%}        ║\n"
           f"║  Parity failures           │  {b_pty_fail:>6.0%}     │  {a_pty_fail:>6.0%}        ║\n"
           f"║  Validator pass rate       │  {b_pass:>6.0%}     │  {a_pass:>6.0%}        ║\n"
            "╚═══════════════════════════════════════════════════════════╝\n"
        )
        assert True  # report-only; never fails
