"""
Quiz quality benchmark — Task 4.2.

Tests the quiz pipeline components directly without LLM calls:
  A. ContentValidator.validate_structure()
  B. ContentValidator.validate_distractors()
  C. ContentValidator.check_alignment()
  D. classify_difficulty()
  E. BM25Scorer — scoring and corpus stats
  F. expand_keywords — synonym expansion
  G. _split_paragraphs — paragraph chunking
  H. _stratified_context — context sampling
  I. LlmQuestionGenerator._is_duplicate() — deduplication
  J. normalize() on quiz output — Indonesian vocab sanitisation
"""
import pytest

from app.services.ai.base import GeneratedQuestion
from app.services.ai.content_validator import ContentValidator, _jaccard
from app.services.ai.quiz_difficulty_classifier import classify_difficulty
from app.services.ai.bm25_scorer import BM25Scorer
from app.services.ai.bm_synonyms import expand_keywords
from app.services.ai.language_normalizer import normalize
from app.repositories.topic_page_repository import _split_paragraphs


# ── Helpers ──────────────────────────────────────────────────────────────────

def _q(
    stem='Apakah nama pengasas Melaka?',
    options=None,
    correct_index=0,
    explanation='Parameswara mengasaskan Melaka.',
    difficulty='mudah',
) -> GeneratedQuestion:
    if options is None:
        options = ['Parameswara', 'Tun Perak', 'Hang Tuah', 'Sultan Mansur Shah']
    return GeneratedQuestion(
        stem=stem,
        options=options,
        correct_index=correct_index,
        explanation=explanation,
        difficulty=difficulty,
    )


# ═══════════════════════════════════════════════════════════════════
# A. ContentValidator.validate_structure()
# ═══════════════════════════════════════════════════════════════════

class TestValidateStructure:

    def test_valid_question_passes(self):
        assert ContentValidator.validate_structure(_q()) is None

    def test_empty_stem_rejected(self):
        q = _q(stem='')
        assert ContentValidator.validate_structure(q) == 'empty stem'

    def test_whitespace_stem_rejected(self):
        q = _q(stem='   ')
        assert ContentValidator.validate_structure(q) == 'empty stem'

    def test_only_three_options_rejected(self):
        q = _q(options=['A', 'B', 'C'])
        err = ContentValidator.validate_structure(q)
        assert err is not None and '4' in err

    def test_five_options_rejected(self):
        q = _q(options=['A', 'B', 'C', 'D', 'E'])
        err = ContentValidator.validate_structure(q)
        assert err is not None and '4' in err

    def test_empty_option_rejected(self):
        q = _q(options=['Parameswara', '', 'Hang Tuah', 'Tun Perak'])
        err = ContentValidator.validate_structure(q)
        assert err is not None and 'option' in err

    def test_correct_index_minus_one_rejected(self):
        q = _q(correct_index=-1)
        err = ContentValidator.validate_structure(q)
        assert err is not None and 'correct_index' in err

    def test_correct_index_four_rejected(self):
        q = _q(correct_index=4)
        err = ContentValidator.validate_structure(q)
        assert err is not None and 'correct_index' in err

    def test_correct_index_three_passes(self):
        q = _q(correct_index=3)
        assert ContentValidator.validate_structure(q) is None

    def test_duplicate_options_rejected(self):
        q = _q(options=['Parameswara', 'Parameswara', 'Hang Tuah', 'Tun Perak'])
        err = ContentValidator.validate_structure(q)
        assert err == 'duplicate options'

    def test_duplicate_options_case_insensitive(self):
        q = _q(options=['parameswara', 'Parameswara', 'Hang Tuah', 'Tun Perak'])
        err = ContentValidator.validate_structure(q)
        assert err == 'duplicate options'

    def test_empty_explanation_rejected(self):
        q = _q(explanation='')
        err = ContentValidator.validate_structure(q)
        assert err == 'empty explanation'

    def test_arabic_script_rejected(self):
        q = _q(stem='ما هو اسم مؤسس ملاكا؟')
        err = ContentValidator.validate_structure(q)
        assert err is not None and 'non-Latin' in err

    def test_chinese_script_rejected(self):
        q = _q(stem='马六甲的创始人是谁？')
        err = ContentValidator.validate_structure(q)
        assert err is not None and 'non-Latin' in err

    def test_valid_bm_with_numbers_passes(self):
        q = _q(
            stem='Pada tahun berapakah Jepun menyerah kalah?',
            options=['1943', '1945', '1947', '1949'],
            correct_index=1,
            explanation='Jepun menyerah kalah pada tahun 1945.',
        )
        assert ContentValidator.validate_structure(q) is None


# ═══════════════════════════════════════════════════════════════════
# B. ContentValidator.validate_distractors()
# ═══════════════════════════════════════════════════════════════════

class TestValidateDistractors:

    def test_good_distractors_pass(self):
        assert ContentValidator.validate_distractors(_q()) is None

    def test_semua_di_atas_flagged(self):
        q = _q(options=['1948', '1955', '1957', 'Semua di atas'], correct_index=2)
        warn = ContentValidator.validate_distractors(q)
        assert warn is not None and 'trivial' in warn

    def test_tiada_yang_betul_flagged(self):
        q = _q(options=['1948', 'Tiada yang betul', '1957', '1963'], correct_index=0)
        warn = ContentValidator.validate_distractors(q)
        assert warn is not None and 'trivial' in warn

    def test_all_of_the_above_english_flagged(self):
        q = _q(options=['Parameswara', 'Hang Tuah', 'Tun Perak', 'All of the above'], correct_index=0)
        warn = ContentValidator.validate_distractors(q)
        assert warn is not None and 'trivial' in warn

    def test_near_duplicate_distractors_flagged(self):
        q = _q(
            options=['Parameswara mengasaskan Melaka', 'Parameswara mengasaskan Melaka baru', 'Tun Perak', 'Hang Tuah'],
            correct_index=2,
        )
        warn = ContentValidator.validate_distractors(q)
        assert warn is not None and 'duplicate' in warn

    def test_distractor_same_as_correct_flagged(self):
        q = _q(options=['Parameswara', 'Parameswara', 'Hang Tuah', 'Tun Perak'], correct_index=0)
        # Note: validate_structure catches duplicate options first, but
        # validate_distractors should also catch correct == distractor
        warn = ContentValidator.validate_distractors(q)
        assert warn is not None

    def test_similar_but_below_threshold_passes(self):
        # "1948" vs "1955" — very different, should pass
        q = _q(
            stem='Pada tahun berapakah perjanjian ini ditandatangani?',
            options=['1948', '1955', '1963', '1971'],
            correct_index=0,
            explanation='Perjanjian ini ditandatangani pada tahun 1948.',
        )
        assert ContentValidator.validate_distractors(q) is None

    def test_plausible_name_distractors_pass(self):
        q = _q(
            stem='Siapakah Perdana Menteri pertama Malaysia?',
            options=['Tunku Abdul Rahman', 'Abdul Razak Hussein', 'Hussein Onn', 'Mahathir Mohamad'],
            correct_index=0,
            explanation='Tunku Abdul Rahman ialah PM pertama Malaysia.',
        )
        assert ContentValidator.validate_distractors(q) is None


# ═══════════════════════════════════════════════════════════════════
# C. ContentValidator.check_alignment()
# ═══════════════════════════════════════════════════════════════════

class TestCheckAlignment:

    CTX = (
        'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau berasal dari Palembang. '
        'Melaka menjadi pusat perdagangan penting di Selat Melaka pada abad ke-15.'
    )

    def test_question_from_context_passes(self):
        q = _q(stem='Siapakah pengasas Kesultanan Melayu Melaka?')
        assert ContentValidator.check_alignment(q, self.CTX) is True

    def test_question_no_overlap_fails(self):
        q = _q(
            stem='Apakah nama presiden Amerika Syarikat yang pertama?',
            options=['George Washington', 'Abraham Lincoln', 'Thomas Jefferson', 'John Adams'],
        )
        result = ContentValidator.check_alignment(q, self.CTX)
        assert result is False

    def test_empty_context_always_passes(self):
        q = _q()
        assert ContentValidator.check_alignment(q, '') is True

    def test_palembang_overlap_detected(self):
        q = _q(
            stem='Dari manakah Parameswara berasal?',
            options=['Palembang', 'Majapahit', 'Siam', 'Singapura'],
        )
        assert ContentValidator.check_alignment(q, self.CTX) is True


# ═══════════════════════════════════════════════════════════════════
# D. classify_difficulty()
# ═══════════════════════════════════════════════════════════════════

class TestClassifyDifficulty:

    # mudah — factual recall
    def test_siapakah_is_mudah(self):
        assert classify_difficulty('Siapakah pengasas Melaka?') == 'mudah'

    def test_bilakah_is_mudah(self):
        assert classify_difficulty('Bilakah Malaysia mencapai kemerdekaan?') == 'mudah'

    def test_di_mana_is_mudah(self):
        assert classify_difficulty('Di manakah perjanjian itu ditandatangani?') == 'mudah'

    def test_apakah_nama_is_mudah(self):
        assert classify_difficulty('Apakah nama akta yang diperkenalkan?') == 'mudah'

    def test_berapa_is_mudah(self):
        assert classify_difficulty('Berapa kalikah pilihan raya diadakan?') == 'mudah'

    # sederhana — applied understanding
    def test_mengapa_is_sederhana(self):
        assert classify_difficulty('Mengapa Melaka jatuh ke tangan Portugis?') == 'sederhana'

    def test_bagaimana_is_sederhana(self):
        assert classify_difficulty('Bagaimanakah sistem pentadbiran British berfungsi?') == 'sederhana'

    def test_apakah_sebab_is_sederhana(self):
        assert classify_difficulty('Apakah sebab berlakunya Perang Dunia Pertama?') == 'sederhana'

    def test_apakah_kesan_is_sederhana(self):
        assert classify_difficulty('Apakah kesan pendudukan Jepun terhadap Tanah Melayu?') == 'sederhana'

    def test_huraikan_is_sederhana(self):
        assert classify_difficulty('Huraikan peranan Parameswara dalam sejarah Melaka.') == 'sederhana'

    # sukar — synthesis / KBAT
    def test_bandingkan_is_sukar(self):
        assert classify_difficulty('Bandingkan sistem pentadbiran Melayu tradisional dengan sistem British.') == 'sukar'

    def test_bezakan_is_sukar(self):
        assert classify_difficulty('Bezakan antara Perjanjian Pangkor 1874 dengan Perjanjian Persekutuan.') == 'sukar'

    def test_nilaikan_is_sukar(self):
        assert classify_difficulty('Nilaikan keberkesanan Dasar Ekonomi Baru dalam mencapai matlamatnya.') == 'sukar'

    def test_sejauh_mana_is_sukar(self):
        assert classify_difficulty('Sejauh manakah pendudukan Jepun mengubah struktur masyarakat Tanah Melayu?') == 'sukar'

    def test_default_is_sederhana(self):
        # No pattern matches → default sederhana
        assert classify_difficulty('Pilih jawapan yang paling tepat.') == 'sederhana'

    # sukar takes priority over sederhana patterns in same stem
    def test_sukar_wins_over_sederhana(self):
        assert classify_difficulty('Bandingkan dan jelaskan perbezaan antara dua sistem ini.') == 'sukar'


# ═══════════════════════════════════════════════════════════════════
# E. BM25Scorer
# ═══════════════════════════════════════════════════════════════════

class TestBM25Scorer:

    def test_empty_corpus(self):
        avg, df, n = BM25Scorer.build_corpus_stats([])
        assert avg == 0.0 and df == {} and n == 0

    def test_single_doc_corpus(self):
        docs = [['parameswara', 'melaka', 'pengasas']]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        assert n == 1
        assert avg == 3.0
        assert df['melaka'] == 1

    def test_score_zero_for_no_query_terms(self):
        docs = [['parameswara', 'melaka']]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        score = BM25Scorer.score([], docs[0], avg, df, n)
        assert score == 0.0

    def test_score_zero_for_empty_doc(self):
        docs = [['parameswara'], []]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        score = BM25Scorer.score(['parameswara'], [], avg, df, n)
        assert score == 0.0

    def test_matching_doc_scores_higher_than_non_matching(self):
        doc_a = ['parameswara', 'melaka', 'pengasas', 'kesultanan', 'melayu']
        doc_b = ['portugis', 'penaklukan', 'albuquerque', 'tentera', 'serangan']
        docs = [doc_a, doc_b]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        query = ['parameswara', 'melaka']
        score_a = BM25Scorer.score(query, doc_a, avg, df, n)
        score_b = BM25Scorer.score(query, doc_b, avg, df, n)
        assert score_a > score_b

    def test_term_not_in_corpus_contributes_zero(self):
        docs = [['melaka', 'pengasas']]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        score = BM25Scorer.score(['jepun'], docs[0], avg, df, n)
        assert score == 0.0

    def test_repeated_term_in_doc_scores_higher(self):
        doc_rich = ['melaka', 'melaka', 'melaka', 'pengasas']
        doc_sparse = ['melaka', 'pengasas', 'portugis', 'serangan']
        docs = [doc_rich, doc_sparse]
        avg, df, n = BM25Scorer.build_corpus_stats(docs)
        query = ['melaka']
        score_rich = BM25Scorer.score(query, doc_rich, avg, df, n)
        score_sparse = BM25Scorer.score(query, doc_sparse, avg, df, n)
        assert score_rich > score_sparse

    def test_tokenize_strips_short_words(self):
        tokens = BM25Scorer.tokenize('di Melaka dan ia')
        assert 'di' not in tokens
        assert 'ia' not in tokens
        assert 'melaka' in tokens

    def test_tokenize_lowercases(self):
        tokens = BM25Scorer.tokenize('Parameswara Melaka')
        assert 'parameswara' in tokens
        assert 'Parameswara' not in tokens


# ═══════════════════════════════════════════════════════════════════
# F. expand_keywords — synonym expansion
# ═══════════════════════════════════════════════════════════════════

class TestExpandKeywords:

    def test_no_synonyms_returns_original(self):
        kws = ['xyz_no_synonym_word']
        assert expand_keywords(kws) == kws

    def test_raja_expands_to_include_sultan(self):
        expanded = expand_keywords(['raja'])
        assert 'sultan' in expanded
        assert 'pemimpin' in expanded

    def test_perang_expands_to_include_pertempuran(self):
        expanded = expand_keywords(['perang'])
        assert 'pertempuran' in expanded

    def test_kemerdekaan_expands(self):
        expanded = expand_keywords(['kemerdekaan'])
        assert 'merdeka' in expanded

    def test_no_duplicates_in_expansion(self):
        expanded = expand_keywords(['raja', 'sultan'])
        assert len(expanded) == len(set(expanded))

    def test_empty_list(self):
        assert expand_keywords([]) == []

    def test_original_order_preserved(self):
        kws = ['perang', 'melaka']
        expanded = expand_keywords(kws)
        assert expanded[0] == 'perang'
        assert expanded[1] == 'melaka'

    def test_unknown_word_not_expanded(self):
        kws = ['parameswara', 'palembang']
        expanded = expand_keywords(kws)
        assert expanded == kws  # no synonyms for proper nouns


# ═══════════════════════════════════════════════════════════════════
# G. _split_paragraphs — paragraph chunking
# ═══════════════════════════════════════════════════════════════════

class TestSplitParagraphs:

    def test_single_paragraph_not_split(self):
        text = 'Parameswara ialah pengasas Melaka. Beliau berasal dari Palembang.'
        chunks = _split_paragraphs(text, 1, 'Bab 1', 1)
        assert len(chunks) == 1
        assert chunks[0]['page_number'] == 1

    def test_two_paragraphs_split(self):
        text = (
            'Parameswara ialah pengasas Melaka. Beliau berasal dari Palembang. '
            'Beliau melarikan diri kerana serangan musuh yang menyerang kawasannya.\n\n'
            'Melaka menjadi pusat perdagangan yang penting. Pedagang dari China dan India '
            'datang berdagang. Selat Melaka menjadi laluan perdagangan yang strategik.'
        )
        # min_words=10 so each ~20-word paragraph stays as its own chunk
        chunks = _split_paragraphs(text, 1, 'Bab 1', 3, min_words=10)
        assert len(chunks) >= 2

    def test_chunks_inherit_page_number(self):
        text = (
            'Parameswara ialah pengasas Melaka pada tahun 1400. Beliau berasal dari Palembang.\n\n'
            'Portugis menakluki Melaka pada tahun 1511 di bawah pimpinan Albuquerque yang terkenal.'
        )
        chunks = _split_paragraphs(text, 2, 'Bab 2', 7)
        for c in chunks:
            assert c['page_number'] == 7
            assert c['topic_id'] == 2
            assert c['topic_name'] == 'Bab 2'

    def test_short_paragraphs_merged(self):
        # Single line too short to be its own chunk — should be merged
        text = 'Pendahuluan.\n\nParameswara ialah pengasas Kesultanan Melayu Melaka yang terkenal.'
        chunks = _split_paragraphs(text, 1, 'Bab 1', 1, min_words=10)
        # Short "Pendahuluan." block should be merged with next paragraph
        assert len(chunks) == 1

    def test_empty_text_returns_nothing(self):
        chunks = _split_paragraphs('', 1, 'Bab 1', 1)
        assert chunks == []

    def test_whitespace_only_returns_nothing(self):
        chunks = _split_paragraphs('   \n\n  ', 1, 'Bab 1', 1)
        assert chunks == []

    def test_chunk_text_not_empty(self):
        text = (
            'Parameswara ialah pengasas Melaka. Beliau berasal dari Palembang dan melarikan diri.\n\n'
            'Melaka berkembang menjadi pusat perdagangan yang penting di rantau ini pada abad ke-15.'
        )
        chunks = _split_paragraphs(text, 1, 'Bab 1', 1)
        for c in chunks:
            assert c['text_content'].strip() != ''


# ═══════════════════════════════════════════════════════════════════
# H. _stratified_context — context sampling
# ═══════════════════════════════════════════════════════════════════

class TestStratifiedContext:
    """Test the _stratified_context helper from quiz_service via import."""

    @pytest.fixture(autouse=True)
    def import_helper(self):
        from app.services.quiz_service import _stratified_context
        self._stratified_context = _stratified_context

    def _make_page(self, content: str):
        class FakePage:
            text_content = content
        return FakePage()

    def test_empty_pages_returns_empty(self):
        assert self._stratified_context([]) == ''

    def test_pages_without_content_ignored(self):
        pages = [self._make_page(''), self._make_page(None), self._make_page('   ')]
        assert self._stratified_context(pages) == ''

    def test_few_pages_all_included(self):
        pages = [self._make_page('Teks A ' * 20), self._make_page('Teks B ' * 20)]
        result = self._stratified_context(pages)
        assert 'Teks A' in result
        assert 'Teks B' in result

    def test_many_pages_sampled_not_truncated_naively(self):
        # 30 pages, last page has unique content
        pages = [self._make_page(f'Halaman {i} ' * 30) for i in range(30)]
        result = self._stratified_context(pages)
        # Stratified: should include content from later pages, not just first 12
        assert 'Halaman 29' in result or 'Halaman 28' in result or 'Halaman 27' in result

    def test_result_under_char_limit(self):
        pages = [self._make_page('X ' * 500) for _ in range(20)]
        result = self._stratified_context(pages)
        assert len(result) <= 7500 + 500  # allow small overshoot from last chunk


# ═══════════════════════════════════════════════════════════════════
# I. LlmQuestionGenerator._is_duplicate()
# ═══════════════════════════════════════════════════════════════════

class TestDeduplication:
    """Test duplicate detection without instantiating the LLM (no API calls)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.ai.llm_generator import LlmQuestionGenerator
        # Patch __init__ to avoid making LLM API calls
        import unittest.mock as mock
        with mock.patch.object(LlmQuestionGenerator, '__init__', return_value=None):
            self.gen = LlmQuestionGenerator()

    def test_identical_stems_are_duplicates(self):
        stem = 'Siapakah pengasas Melaka?'
        assert self.gen._is_duplicate(stem, [stem]) is True

    def test_very_similar_stems_are_duplicates(self):
        stem1 = 'Siapakah pengasas Kesultanan Melayu Melaka?'
        stem2 = 'Siapakah pengasas Melaka?'
        assert self.gen._is_duplicate(stem1, [stem2]) is True

    def test_different_stems_not_duplicates(self):
        stem1 = 'Siapakah pengasas Melaka?'
        stem2 = 'Pada tahun berapakah Portugis menakluki Melaka?'
        assert self.gen._is_duplicate(stem1, [stem2]) is False

    def test_empty_history_never_duplicate(self):
        assert self.gen._is_duplicate('Siapakah pengasas Melaka?', []) is False

    def test_partial_overlap_below_threshold_not_duplicate(self):
        # "Melaka" appears in both but stems are otherwise different
        stem1 = 'Siapakah pengasas Melaka?'
        stem2 = 'Apakah kesan perdagangan di Melaka pada abad ke-15?'
        assert self.gen._is_duplicate(stem1, [stem2]) is False

    def test_multiple_previous_stems_checks_all(self):
        stem = 'Mengapa Melaka penting dalam perdagangan?'
        previous = [
            'Siapakah pengasas Melaka?',
            'Pada tahun berapakah Jepun menyerang?',
            'Mengapa Melaka sangat penting dalam perdagangan Selat?',  # near-duplicate
        ]
        assert self.gen._is_duplicate(stem, previous) is True


# ═══════════════════════════════════════════════════════════════════
# J. normalize() on quiz output
# ═══════════════════════════════════════════════════════════════════

class TestNormalizeQuizOutput:

    def test_bahwa_replaced_in_explanation(self):
        text = 'Ini membuktikan bahwa Parameswara ialah pengasas Melaka.'
        result = normalize(text)
        assert 'bahwa' not in result
        assert 'bahawa' in result

    def test_karena_replaced_in_stem(self):
        text = 'Mengapa Parameswara melarikan diri karena serangan musuh?'
        result = normalize(text)
        assert 'karena' not in result
        assert 'kerana' in result

    def test_kontribusi_replaced_in_option(self):
        text = 'Sumbangan / kontribusi beliau sangat besar.'
        result = normalize(text)
        assert 'kontribusi' not in result

    def test_memiliki_replaced(self):
        text = 'Melaka memiliki kedudukan yang strategik.'
        result = normalize(text)
        assert 'memiliki' not in result
        assert 'mempunyai' in result

    def test_clean_bm_unchanged(self):
        text = 'Parameswara ialah pengasas Melaka yang memerintah dengan bijaksana.'
        result = normalize(text)
        assert result == text

    def test_unicode_normalized(self):
        # NFC normalization — no visible change but internally normalized
        text = 'Parameswara'
        result = normalize(text)
        assert isinstance(result, str)
        assert len(result) > 0


# ═══════════════════════════════════════════════════════════════════
# K. _jaccard helper
# ═══════════════════════════════════════════════════════════════════

class TestJaccard:

    def test_identical_strings_score_one(self):
        assert _jaccard('parameswara melaka', 'parameswara melaka') == 1.0

    def test_completely_different_strings_score_zero(self):
        assert _jaccard('parameswara melaka', 'jepun tentera serangan') == 0.0

    def test_partial_overlap(self):
        score = _jaccard('parameswara melaka pengasas', 'melaka pengasas portugis')
        assert 0.0 < score < 1.0

    def test_empty_strings(self):
        assert _jaccard('', '') == 1.0

    def test_one_empty_string(self):
        assert _jaccard('parameswara', '') == 0.0


# ═══════════════════════════════════════════════════════════════════
# L. validate_stem_quality — ALL-CAPS gibberish rejection
# ═══════════════════════════════════════════════════════════════════

class TestValidateStemQualityNew:

    def test_allcaps_gibberish_rejected(self):
        q = _q(stem='Siapakah YANG ADALAH PENGACAR yang BESAR dalam sejarah?')
        err = ContentValidator.validate_stem_quality(q)
        assert err is not None and 'ALL-CAPS' in err

    def test_normal_question_with_acronym_passes(self):
        # Legitimate acronym — only one ALLCAPS token, below the threshold of 2
        q = _q(stem='Apakah kepanjangan bagi UMNO dalam politik Malaysia?')
        err = ContentValidator.validate_stem_quality(q)
        assert err is None

    def test_two_short_caps_not_rejected(self):
        # Single caps word (3 chars or shorter) should not trigger
        q = _q(stem='Apakah nama PM yang berkhidmat pada era DEB di Malaysia?')
        err = ContentValidator.validate_stem_quality(q)
        assert err is None

    def test_essay_starter_still_rejected(self):
        q = _q(stem='Huraikan peranan Parameswara dalam sejarah Melaka?')
        err = ContentValidator.validate_stem_quality(q)
        assert err is not None and 'essay' in err

    def test_no_question_mark_still_rejected(self):
        q = _q(stem='Apakah nama pengasas Melaka')
        err = ContentValidator.validate_stem_quality(q)
        assert err == 'stem does not end with question mark'


# ═══════════════════════════════════════════════════════════════════
# M. validate_options_clean — option-label leakage detection
# ═══════════════════════════════════════════════════════════════════

class TestValidateOptionsClean:

    def test_clean_options_pass(self):
        q = _q(options=['Parameswara', 'Hang Tuah', 'Tun Perak', 'Sultan Mansur Shah'])
        assert ContentValidator.validate_options_clean(q) is None

    def test_option_with_a_dot_prefix_detected(self):
        q = _q(options=[
            'A. Parameswara mengasaskan Melaka',
            'Hang Tuah',
            'Tun Perak',
            'Sultan Mansur Shah',
        ])
        err = ContentValidator.validate_options_clean(q)
        assert err is not None and 'label prefix' in err

    def test_lowercase_a_dot_prefix_also_detected(self):
        q = _q(options=[
            'a. parameswara',
            'Hang Tuah',
            'Tun Perak',
            'Sultan Mansur',
        ])
        err = ContentValidator.validate_options_clean(q)
        assert err is not None

    def test_d_dot_prefix_detected(self):
        q = _q(options=[
            'Parameswara',
            'Hang Tuah',
            'Tun Perak',
            'D. Sultan Mansur Shah',
        ], correct_index=3)
        err = ContentValidator.validate_options_clean(q)
        assert err is not None

    def test_option_starting_with_d_word_not_rejected(self):
        # "Dasar Ekonomi Baru" starts with 'D' but isn't a label prefix
        q = _q(options=['Dasar Ekonomi Baru', 'Dasar Pandang Timur', 'Wawasan 2020', 'Dasar Nasional'])
        assert ContentValidator.validate_options_clean(q) is None


# ═══════════════════════════════════════════════════════════════════
# N. Prompt template — angle system coverage
# ═══════════════════════════════════════════════════════════════════

class TestAngleSystem:

    def test_ten_angles_defined(self):
        # Phase 1 added the Roman Numeral angle — now 11 total
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        assert len(QUESTION_ANGLES_BM) == 11

    def test_three_cognitive_tiers_present(self):
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        tiers = {angle[2] for angle in QUESTION_ANGLES_BM}
        assert 'recall' in tiers
        assert 'application' in tiers
        assert 'hots' in tiers

    def test_three_hots_angles_present(self):
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        hots = [a for a in QUESTION_ANGLES_BM if a[2] == 'hots']
        assert len(hots) == 3

    def test_pick_angle_returns_tuple(self):
        from app.services.ai.prompt_templates import pick_angle
        result = pick_angle(0)
        assert isinstance(result, tuple) and len(result) == 3
        name, instruction, tier = result
        assert isinstance(name, str) and len(name) > 0
        assert isinstance(instruction, str) and len(instruction) > 0
        assert tier in ('recall', 'application', 'hots')

    def test_shuffled_order_covers_all_angles(self):
        from app.services.ai.prompt_templates import make_shuffled_angle_order, QUESTION_ANGLES_BM
        n = len(QUESTION_ANGLES_BM)  # 11
        order = make_shuffled_angle_order(n)
        # First n entries should cover all n angle indices exactly once
        assert sorted(order[:n]) == list(range(n))

    def test_shuffled_order_is_random(self):
        from app.services.ai.prompt_templates import make_shuffled_angle_order
        orders = [tuple(make_shuffled_angle_order(10)[:10]) for _ in range(10)]
        # At least 2 different orderings in 10 samples (probability 1 - 1/10! ≈ 100%)
        assert len(set(orders)) > 1

    def test_pick_angle_with_shuffled_order(self):
        from app.services.ai.prompt_templates import pick_angle, make_shuffled_angle_order
        order = make_shuffled_angle_order(10)
        results = [pick_angle(i, order) for i in range(10)]
        # All tiers should appear in a 10-question set
        tiers = {r[2] for r in results}
        assert 'recall' in tiers
        assert 'application' in tiers
        assert 'hots' in tiers

    def test_shuffled_order_covers_budget(self):
        """make_shuffled_angle_order must return enough indices for the full budget."""
        from app.services.ai.prompt_templates import make_shuffled_angle_order, QUESTION_ANGLES_BM
        budget = 44  # 11 questions × _BUDGET_MULTIPLIER=4
        order = make_shuffled_angle_order(budget)
        assert len(order) >= budget
        # All indices must be valid angle positions
        assert all(0 <= idx < len(QUESTION_ANGLES_BM) for idx in order)

    def test_roman_numeral_angle_is_application_tier(self):
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        rn_angles = [a for a in QUESTION_ANGLES_BM if 'roman numeral' in a[0].lower() or 'pelbagai pernyataan' in a[0].lower()]
        assert len(rn_angles) == 1, 'exactly one Roman Numeral angle expected'
        assert rn_angles[0][2] == 'application'

    def test_five_application_angles_present(self):
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        app_angles = [a for a in QUESTION_ANGLES_BM if a[2] == 'application']
        assert len(app_angles) == 5  # 4 original + 1 RN

    def test_application_angles_have_anti_recall_guards(self):
        """Phase 1: Application/HOTS angle instructions must contain explicit anti-recall language."""
        from app.services.ai.prompt_templates import QUESTION_ANGLES_BM
        anti_recall_keywords = ['jangan', 'mesti', 'memahami', 'analisis', 'bukan sekadar']
        non_recall_angles = [a for a in QUESTION_ANGLES_BM if a[2] in ('application', 'hots')]
        for name, instruction, tier in non_recall_angles:
            if 'roman numeral' in name.lower() or 'pelbagai' in name.lower():
                continue  # RN angle has its own format constraints
            instr_lower = instruction.lower()
            has_guard = any(kw in instr_lower for kw in anti_recall_keywords)
            assert has_guard, (
                f'Application/HOTS angle "{name}" lacks anti-recall guard. '
                f'Add explicit instruction preventing recall-style output.'
            )


# ═══════════════════════════════════════════════════════════════════
# O. Budget-based generation loop (LlmQuestionGenerator internals)
# ═══════════════════════════════════════════════════════════════════

class TestBudgetBasedGeneration:
    """Unit tests for the budget-based 'generate until N' loop.

    The generator uses a while loop with a budget cap so that validation
    failures and dedup rejects don't permanently consume question slots.
    These tests use a fake _generate_one_with_retries to control outcomes.
    """

    def _make_question(self, stem: str) -> 'GeneratedQuestion':
        return GeneratedQuestion(
            stem=stem,
            options=['A satu', 'B dua', 'C tiga', 'D empat'],
            correct_index=0,
            explanation='Penjelasan ujian.',
            difficulty='mudah',
        )

    def test_reaches_target_despite_initial_failures(self):
        """Generator produces N questions even if the first K attempts fail."""
        from unittest.mock import patch, MagicMock
        from app.services.ai.llm_generator import LlmQuestionGenerator

        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        call_count = 0

        def fake_retries(ctx, stems, angle_name, angle_instruction):
            nonlocal call_count
            call_count += 1
            # Fail the first 5 attempts, then succeed
            if call_count <= 5:
                return None
            return self._make_question(f'Soalan {call_count}?')

        with patch.object(gen, '_generate_one_with_retries', side_effect=fake_retries):
            results = list(gen.generate_stream('some context', num_questions=3))

        assert len(results) == 3
        assert call_count > 3  # required more attempts than questions

    def test_budget_cap_prevents_infinite_loop(self):
        """If every attempt fails, loop stops at budget and yields nothing."""
        from unittest.mock import patch
        from app.services.ai.llm_generator import LlmQuestionGenerator

        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        outer_attempts = []

        def always_fail(ctx, stems, angle_name, angle_instruction):
            outer_attempts.append(1)
            return None

        with patch.object(gen, '_generate_one_with_retries', side_effect=always_fail):
            results = list(gen.generate_stream('ctx', num_questions=3))

        assert results == []
        # Budget = 3 × _BUDGET_MULTIPLIER (4) = 12 outer attempts max
        assert len(outer_attempts) == 3 * LlmQuestionGenerator._BUDGET_MULTIPLIER

    def test_dedup_reject_does_not_consume_slot(self):
        """A duplicate question does not permanently waste a question slot."""
        from unittest.mock import patch
        from app.services.ai.llm_generator import LlmQuestionGenerator

        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        call_count = [0]

        def alternating(ctx, stems, angle_name, angle_instruction):
            call_count[0] += 1
            # Odd calls return the SAME stem (will be deduped after the first)
            # Even calls return a unique stem
            if call_count[0] % 2 == 1:
                return self._make_question('Soalan yang sama?')
            return self._make_question(f'Soalan unik {call_count[0]}?')

        with patch.object(gen, '_generate_one_with_retries', side_effect=alternating):
            results = list(gen.generate_stream('ctx', num_questions=2))

        # Should have yielded exactly 2 unique questions
        assert len(results) == 2
        # The first unique question ('Soalan yang sama?') plus one unique question
        stems = {r.stem for r in results}
        assert len(stems) == 2

    def test_seen_stems_seed_dedup_list(self):
        """seen_stems from previous attempts are respected at the cross-attempt threshold."""
        from unittest.mock import patch
        from app.services.ai.llm_generator import LlmQuestionGenerator

        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        # Produce an identical stem — Jaccard=1.0, blocked even at 0.75
        def always_identical(ctx, stems, angle_name, angle_instruction):
            return self._make_question('Soalan lama yang sama persis?')

        historical = ['Soalan lama yang sama persis?']

        with patch.object(gen, '_generate_one_with_retries', side_effect=always_identical):
            results = list(gen.generate_stream('ctx', num_questions=1, seen_stems=historical))

        assert results == []

    def test_is_duplicate_threshold_parameter(self):
        """_is_duplicate respects the threshold argument."""
        from app.services.ai.llm_generator import LlmQuestionGenerator
        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        # Jaccard ≈ 0.6 between these two stems
        new_stem  = 'Apakah kesan Revolusi Amerika yang berlaku pada tahun 1776 terhadap dunia?'
        hist_stem = 'Apakah kesan daripada Revolusi Amerika yang berlaku pada tahun 1776?'

        # Blocked at strict within-run threshold
        assert gen._is_duplicate(new_stem, [hist_stem], threshold=0.5) is True
        # Passes at lenient cross-attempt threshold
        assert gen._is_duplicate(new_stem, [hist_stem], threshold=0.75) is False

    def test_cross_attempt_threshold_allows_different_angle_same_fact(self):
        """A question about the same fact from a different angle passes cross-attempt dedup."""
        from unittest.mock import patch
        from app.services.ai.llm_generator import LlmQuestionGenerator

        gen = LlmQuestionGenerator.__new__(LlmQuestionGenerator)

        # historical stem: asks about "kesan" (effect)
        hist = 'Apakah kesan daripada Revolusi Amerika yang berlaku pada tahun 1776?'
        # new stem: asks about "kepentingan" (significance) — different angle, same fact
        new_q = 'Apakah kepentingan Revolusi Amerika yang berlaku pada tahun 1776 kepada dunia?'

        # Jaccard ≈ 0.55 → blocked at 0.5, passes at 0.75
        call_count = [0]
        def produce_new_angle(ctx, stems, angle_name, angle_instruction):
            call_count[0] += 1
            if call_count[0] == 1:
                return self._make_question(new_q)
            return self._make_question(f'Soalan berbeza {call_count[0]}?')

        with patch.object(gen, '_generate_one_with_retries', side_effect=produce_new_angle):
            results = list(gen.generate_stream('ctx', num_questions=1, seen_stems=[hist]))

        # With two-tier threshold, the different-angle question passes cross-attempt dedup
        assert len(results) == 1
        assert results[0].stem == new_q


# ═══════════════════════════════════════════════════════════════════
# P. Roman Numeral validator
# ═══════════════════════════════════════════════════════════════════

class TestRomanNumeralValidator:
    """Tests for ContentValidator.validate_roman_numeral() — Phase 1."""

    def _rn_q(
        self,
        stem=None,
        options=None,
        correct_index=0,
    ) -> GeneratedQuestion:
        if stem is None:
            stem = (
                'I Amerika menentang cukai tanpa perwakilan British\n'
                'II Revolusi Amerika tercetus pada tahun 1776\n'
                'III Thomas Jefferson memimpin tentera dalam pertempuran\n\n'
                'Antara pernyataan di atas, yang manakah BETUL?'
            )
        if options is None:
            options = [
                'I dan II sahaja',
                'I dan III sahaja',
                'II dan III sahaja',
                'I, II dan III',
            ]
        return GeneratedQuestion(
            stem=stem,
            options=options,
            correct_index=correct_index,
            explanation='I dan II adalah betul berdasarkan teks.',
            difficulty='sederhana',
        )

    def test_valid_rn_question_passes(self):
        assert ContentValidator.validate_roman_numeral(self._rn_q()) is None

    def test_non_rn_question_skipped(self):
        """validate_roman_numeral returns None for regular (non-RN) questions."""
        regular = _q()  # helper from module level
        assert ContentValidator.validate_roman_numeral(regular) is None

    def test_rn_missing_markers_in_stem_rejected(self):
        """Stem without Roman numeral markers is invalid for an RN question."""
        bad = self._rn_q(
            stem='Soalan biasa tanpa pernyataan?\n\nAntara pernyataan di atas, yang manakah BETUL?'
        )
        err = ContentValidator.validate_roman_numeral(bad)
        assert err is not None
        assert 'marker' in err.lower() or 'roman' in err.lower()

    def test_rn_missing_closing_line_rejected(self):
        """Stem that does not close with 'yang manakah ... betul?' is invalid."""
        bad = self._rn_q(
            stem=(
                'I Amerika menentang cukai tanpa perwakilan\n'
                'II Revolusi Amerika tercetus 1776\n'
                'III Jefferson menulis Perisytiharan\n\n'
                'Ini bukan soalan.'
            )
        )
        err = ContentValidator.validate_roman_numeral(bad)
        assert err is not None

    def test_rn_non_subset_options_rejected(self):
        """Options that are regular text (not RN subsets) are invalid."""
        bad = self._rn_q(
            options=[
                'George Washington',
                'Thomas Jefferson',
                'Benjamin Franklin',
                'John Adams',
            ]
        )
        err = ContentValidator.validate_roman_numeral(bad)
        assert err is not None
        assert 'option' in err.lower()

    def test_rn_passes_all_standard_validators(self):
        """A well-formed RN question passes all five standard validators."""
        q = self._rn_q()
        assert ContentValidator.validate_structure(q) is None
        assert ContentValidator.validate_stem_quality(q) is None
        assert ContentValidator.validate_options_clean(q) is None
        assert ContentValidator.validate_roman_numeral(q) is None
        assert ContentValidator.validate_distractors(q) is None

    def test_rn_stem_length_up_to_350_allowed(self):
        """RN stems up to 350 chars pass stem-quality check."""
        long_stem = (
            'I Revolusi Amerika berlaku disebabkan penindasan cukai tanpa perwakilan oleh British\n'
            'II Thomas Jefferson bersama kongres meluluskan Perisytiharan Kemerdekaan pada 1776\n'
            'III Revolusi Amerika memberi inspirasi kepada gerakan nasionalisme di Asia Tenggara\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        )
        assert len(long_stem) <= 350
        q = self._rn_q(stem=long_stem)
        assert ContentValidator.validate_stem_quality(q) is None

    def test_rn_stem_over_350_rejected(self):
        """RN stems exceeding 350 chars are still rejected."""
        padding = 'X' * 300
        long_stem = (
            f'I {padding}\n'
            'II Revolusi berlaku 1776\n'
            'III Jefferson menulis dokumen\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        )
        assert len(long_stem) > 350
        q = self._rn_q(stem=long_stem)
        err = ContentValidator.validate_stem_quality(q)
        assert err is not None and 'too long' in err

    def test_is_roman_numeral_detection_requires_two_rn_options(self):
        """_is_roman_numeral_question needs at least 2 RN-format options to fire."""
        from app.services.ai.content_validator import ContentValidator
        # Only 1 RN-style option → not detected as RN
        q_one = _q(options=['I dan II sahaja', 'George Washington', 'Thomas Jefferson', 'Benjamin Franklin'])
        assert ContentValidator._is_roman_numeral_question(q_one) is False
        # 2 RN-style options → detected
        q_two = _q(options=['I dan II sahaja', 'I dan III sahaja', 'Thomas Jefferson', 'Benjamin Franklin'])
        assert ContentValidator._is_roman_numeral_question(q_two) is True


class TestOptionLengthParity:
    """Phase 2 — validate_option_length_parity() unit tests."""

    def test_balanced_options_pass(self):
        """Options with similar lengths (ratio < 3.0) should pass."""
        q = _q(options=['Kuala Lumpur', 'George Town', 'Putrajaya', 'Johor Bahru'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is None

    def test_extreme_imbalance_rejected(self):
        """Shortest 4 chars vs longest 16 chars → 4:1 ratio → rejected."""
        q = _q(options=['Ipoh', 'Amerika Syarikat', 'Kuala Lumpur', 'George Town'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is not None
        assert 'imbalance' in err

    def test_exactly_3_to_1_ratio_rejected(self):
        """Ratio exactly 3.0 triggers rejection (threshold is >=3.0)."""
        short = 'AB'          # 2 chars
        long_ = 'ABCDEF'      # 6 chars  → 6/2 = 3.0
        q = _q(options=[short, long_, 'ABCD', 'ABCDE'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is not None

    def test_just_below_threshold_passes(self):
        """Ratio below 3.0 should pass."""
        short = 'ABC'         # 3 chars
        long_ = 'ABCDEFGH'   # 8 chars → 8/3 = 2.67
        q = _q(options=[short, long_, 'ABCDE', 'ABCDEF'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is None

    def test_rn_question_exempt(self):
        """Roman Numeral questions are exempt from parity check."""
        rn_stem = (
            'I Amerika menentang cukai tanpa perwakilan\n'
            'II Revolusi berlaku pada 1776\n'
            'III Jefferson menulis Perisytiharan Kemerdekaan\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        )
        # RN options have inherently different lengths
        q = _q(
            stem=rn_stem,
            options=['I dan II sahaja', 'I dan III sahaja', 'II dan III sahaja', 'I, II dan III'],
        )
        err = ContentValidator.validate_option_length_parity(q)
        assert err is None

    def test_report_shows_short_and_long_option(self):
        """Error message should quote both the short and the long option."""
        q = _q(options=['Ipoh', 'Amerika Syarikat', 'Kuala Lumpur', 'George Town'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is not None
        assert 'Ipoh' in err
        assert 'Amerika Syarikat' in err

    def test_single_char_option_rejected(self):
        """A 1-char option next to a 4+-char option triggers rejection."""
        q = _q(options=['A', 'Kuala Lumpur', 'George Town', 'Johor Bahru'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is not None

    def test_equal_length_options_pass(self):
        """All options same length should pass."""
        q = _q(options=['ABCD', 'EFGH', 'IJKL', 'MNOP'])
        err = ContentValidator.validate_option_length_parity(q)
        assert err is None


class TestOptionParallelism:
    """Phase 3 — validate_option_parallelism() unit tests."""

    def test_all_four_me_verbs_pass(self):
        """Four meN- verb options → grammatically parallel → pass."""
        q = _q(options=[
            'Mengembangkan ekonomi negara',
            'Meningkatkan pendapatan rakyat',
            'Memajukan sektor industri',
            'Mengurangkan kadar kemiskinan',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is None

    def test_three_me_verbs_one_other_rejected(self):
        """3 meN- verbs + 1 non-verb → non-parallel → rejected."""
        q = _q(options=[
            'Mengembangkan ekonomi negara',
            'Meningkatkan pendapatan rakyat',
            'Memajukan sektor industri',
            'Ekonomi negara bertumbuh pesat',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is not None
        assert 'parallel' in err

    def test_two_me_verbs_not_treated_as_action_type(self):
        """Only 2 meN- openers → ambiguous, not treated as action question → pass."""
        q = _q(options=[
            'Mengembangkan ekonomi',
            'Meningkatkan pendapatan',
            '1776',
            'George Washington',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is None

    def test_non_action_options_pass(self):
        """Date/name/place options require no parallelism check."""
        q = _q(options=['Kuala Lumpur', 'George Town', 'Putrajaya', 'Johor Bahru'])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is None

    def test_rn_question_exempt(self):
        """Roman Numeral questions skip the parallelism check."""
        rn_stem = (
            'I Amerika menentang cukai tanpa perwakilan\n'
            'II Revolusi berlaku pada 1776\n'
            'III Jefferson menulis Perisytiharan Kemerdekaan\n\n'
            'Antara pernyataan di atas, yang manakah BETUL?'
        )
        q = _q(
            stem=rn_stem,
            options=['I dan II sahaja', 'I dan III sahaja', 'II dan III sahaja', 'I, II dan III'],
        )
        err = ContentValidator.validate_option_parallelism(q)
        assert err is None

    def test_error_message_contains_non_parallel_option(self):
        """Error should quote the option that broke parallelism."""
        q = _q(options=[
            'Mengembangkan ekonomi',
            'Meningkatkan pendapatan',
            'Memajukan industri',
            'Ekonomi berkembang',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is not None
        assert 'Ekonomi berkembang' in err

    def test_passive_voice_breaks_parallelism(self):
        """Passive constructions (di-) among meN- options → rejected."""
        q = _q(options=[
            'Mengembangkan ekonomi',
            'Meningkatkan pendapatan',
            'Memajukan industri',
            'Dikurangkan kemiskinan',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is not None

    def test_all_passive_not_action_type(self):
        """All di- passive options → fewer than 3 meN- → not action-type → pass."""
        q = _q(options=[
            'Dikembangkan oleh kerajaan',
            'Ditingkatkan pendapatan',
            'Dimajukan industri',
            'Dikurangkan kemiskinan',
        ])
        err = ContentValidator.validate_option_parallelism(q)
        assert err is None
