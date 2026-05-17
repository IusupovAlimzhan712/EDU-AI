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
  I. OllamaQuestionGenerator._is_duplicate() — deduplication
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
# I. OllamaQuestionGenerator._is_duplicate()
# ═══════════════════════════════════════════════════════════════════

class TestDeduplication:
    """Test duplicate detection without instantiating Ollama (no LLM calls)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.ai.ollama_generator import OllamaQuestionGenerator
        # Patch __init__ to avoid connecting to Ollama
        import unittest.mock as mock
        with mock.patch.object(OllamaQuestionGenerator, '__init__', return_value=None):
            self.gen = OllamaQuestionGenerator()

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
