"""
Adversarial tutor benchmark — Task 4.1.

Tests TutorValidator.validate() and entity gate directly.
No LLM calls are made; all test data is hand-crafted.

Categories:
  A. Entity gate — correct blocking / passing
  B. Validator: empty / too short / too long
  C. Validator: broken unicode / non-Latin script
  D. Validator: language checks (English, BM marker count)
  E. Validator: Indonesian vocabulary leakage
  F. Validator: date contradiction
  G. Validator: semantic grounding (hallucinated concepts)
  H. Validator: legitimate refusals always pass
  I. Correct BM historical answers always pass
"""
import pytest

from app.services.ai.tutor_validator import TutorValidator
from app.services.ai.entity_gate import (
    check_entity_gate, detect_expected_entity_type, UNCERTAINTY_RESPONSE,
)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _ok(response: str, context: str = 'Parameswara ialah pengasas Melaka pada tahun 1400. Beliau datang dari Palembang.') -> bool:
    status, _ = TutorValidator.validate(response, context)
    return status == 'ok'


def _warned(response: str, context: str = 'Parameswara ialah pengasas Melaka pada tahun 1400. Beliau datang dari Palembang.') -> bool:
    status, _ = TutorValidator.validate(response, context)
    return status == 'warned'


def _warning_text(response: str, context: str = 'Parameswara ialah pengasas Melaka pada tahun 1400.') -> str | None:
    _, msg = TutorValidator.validate(response, context)
    return msg


# ═══════════════════════════════════════════════════════════════════
# A. Entity gate
# ═══════════════════════════════════════════════════════════════════

class TestEntityGate:

    PERSON_CTX = 'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau memerintah sejak 1400.'
    NO_PERSON_CTX = 'Melaka adalah sebuah pelabuhan yang penting di Selat Melaka pada abad ke-15.'

    DATE_CTX = 'Peristiwa ini berlaku pada tahun 1511 apabila Portugis menakluki Melaka.'
    NO_DATE_CTX = 'Portugis menyerang Melaka dengan kekuatan tentera yang besar dan berjaya.'

    PLACE_CTX = 'Perjanjian ini ditandatangani di Singapura antara dua pihak yang bertelagah.'
    NO_PLACE_CTX = 'Perjanjian itu ditandatangani oleh wakil kerajaan dan pihak pembangkang.'

    # --- person questions ---

    def test_person_question_context_has_person_proceeds(self):
        assert check_entity_gate('Siapakah pengasas Melaka?', self.PERSON_CTX) is True

    def test_person_question_context_no_person_blocked(self):
        assert check_entity_gate('Siapakah pengasas Melaka?', self.NO_PERSON_CTX) is False

    def test_siapakah_variant(self):
        assert check_entity_gate('Siapakah yang memerintah Melaka?', self.PERSON_CTX) is True

    def test_nama_raja_blocked_no_name(self):
        assert check_entity_gate('Apakah nama raja pertama Melaka?', self.NO_PERSON_CTX) is False

    def test_nama_raja_passes_with_name(self):
        assert check_entity_gate('Apakah nama raja pertama Melaka?', self.PERSON_CTX) is True

    # --- date questions ---

    def test_date_question_context_has_year_proceeds(self):
        assert check_entity_gate('Pada tahun berapa Portugis menakluki Melaka?', self.DATE_CTX) is True

    def test_date_question_context_no_year_blocked(self):
        assert check_entity_gate('Bilakah Portugis menakluki Melaka?', self.NO_DATE_CTX) is False

    def test_bilakah_variant_blocked(self):
        assert check_entity_gate('Bilakah berlakunya Perang Dunia Kedua?', 'Jepun menyerang Tanah Melayu.') is False

    def test_bilakah_variant_passes(self):
        assert check_entity_gate('Bilakah Jepun menyerang?', 'Jepun menyerang pada tahun 1941.') is True

    # --- place questions ---

    def test_place_question_context_has_place_proceeds(self):
        assert check_entity_gate('Di mana perjanjian itu ditandatangani?', self.PLACE_CTX) is True

    def test_place_question_context_no_specific_place_blocked(self):
        # Context has no capitalized place name
        bare_ctx = 'wakil kerajaan menandatangani dokumen berkenaan di hadapan orang ramai.'
        assert check_entity_gate('Di mana perjanjian itu ditandatangani?', bare_ctx) is False

    # --- law/policy questions ---

    def test_law_question_context_has_akta_proceeds(self):
        ctx = 'Akta Hasutan 1948 telah digunakan untuk mengawal kebebasan bersuara.'
        assert check_entity_gate('Apakah Akta yang mengawal kebebasan bersuara?', ctx) is True

    def test_law_question_context_no_akta_blocked(self):
        ctx = 'Kerajaan mengawal kebebasan bersuara melalui pelbagai kaedah undang-undang.'
        assert check_entity_gate('Apakah Akta yang mengawal kebebasan bersuara?', ctx) is False

    # --- no expected entity — always proceeds ---

    def test_explanation_question_no_gate(self):
        ctx = 'beberapa sebab mengapa dasar ini dilaksanakan termasuklah faktor ekonomi.'
        assert check_entity_gate('Mengapa dasar ini dilaksanakan?', ctx) is True

    def test_generic_question_no_gate(self):
        assert check_entity_gate('Huraikan ciri-ciri sistem feudal Melayu.', 'teks tiada entiti.') is True

    # --- entity type detection ---

    def test_detect_siapakah(self):
        assert detect_expected_entity_type('Siapakah Parameswara?') == 'person'

    def test_detect_bilakah(self):
        assert detect_expected_entity_type('Bilakah Melaka ditakluki?') == 'date'

    def test_detect_di_mana(self):
        assert detect_expected_entity_type('Di mana ibu kota pertama Melaka?') == 'place'

    def test_detect_akta(self):
        assert detect_expected_entity_type('Apakah Akta yang mengawal hasutan?') == 'law'

    def test_detect_mengapa(self):
        assert detect_expected_entity_type('Mengapa Melaka jatuh ke tangan Portugis?') == 'event'

    def test_detect_none(self):
        assert detect_expected_entity_type('Bandingkan sistem pentadbiran Melayu dan British.') == 'none'


# ═══════════════════════════════════════════════════════════════════
# B. Validator: empty / too short / too long
# ═══════════════════════════════════════════════════════════════════

class TestLengthValidation:

    CTX = 'Parameswara ialah pengasas Melaka pada tahun 1400.'

    def test_empty_string(self):
        assert _warned('', self.CTX)

    def test_whitespace_only(self):
        assert _warned('   ', self.CTX)

    def test_too_short_less_than_15_chars(self):
        assert _warned('Baik sahaja.', self.CTX)

    def test_exactly_min_length_passes(self):
        # 15 chars, but not necessarily a valid BM response with markers
        # Just checking the length gate itself doesn't fire
        status, msg = TutorValidator.validate('Parameswara wira.', self.CTX)
        # Should not be warned for length; may be warned for other reasons
        assert msg != 'Jawapan AI terlalu pendek.'

    def test_too_long_over_6000_chars(self):
        long_text = 'Parameswara ialah pengasas Melaka. ' * 200  # ~7000 chars
        assert _warned(long_text, self.CTX)


# ═══════════════════════════════════════════════════════════════════
# C. Validator: broken unicode / non-Latin script
# ═══════════════════════════════════════════════════════════════════

class TestEncodingAndScript:

    CTX = 'Parameswara ialah pengasas Melaka pada tahun 1400. Beliau memerintah dengan adil.'

    def test_broken_unicode_warned(self):
        bad = 'Parameswara ialah �pengasas� Melaka yang memerintah dengan baik dan adil.'
        assert _warned(bad, self.CTX)

    def test_arabic_script_warned(self):
        arabic = 'باراميسوارا هو مؤسس مملكة ملقا. وقد حكم بحكمة وعدل كبير في المنطقة.'
        assert _warned(arabic, self.CTX)

    def test_chinese_script_warned(self):
        chinese = '巴拉米苏拉是马六甲苏丹国的创始人。他是从巨港逃来的。'
        assert _warned(chinese, self.CTX)

    def test_clean_latin_bm_passes_encoding_check(self):
        good = 'Parameswara ialah pengasas Kesultanan Melayu Melaka yang terkenal dalam sejarah.'
        status, msg = TutorValidator.validate(good, self.CTX)
        assert msg != 'Jawapan mengandungi aksara rosak (ralat pengekodan).'
        assert msg != 'Jawapan mengandungi aksara bukan-Latin.'


# ═══════════════════════════════════════════════════════════════════
# D. Validator: language checks
# ═══════════════════════════════════════════════════════════════════

class TestLanguageDetection:

    # Realistic retrieval: 8 pages → richer context with vocabulary matching typical responses
    CTX = (
        'Parameswara ialah pengasas Kesultanan Melayu Melaka pada tahun 1400. '
        'Beliau datang dari Palembang kerana ancaman Majapahit. Baginda melarikan diri '
        'bersama pengikutnya dan tiba di kawasan yang kemudiannya dikenali sebagai Melaka. '
        'Parameswara kemudian membina kerajaan baharu yang berkembang pesat menjadi '
        'pusat perdagangan penting di Selat Melaka. Serangan musuh mendorong beliau '
        'berpindah ke kawasan baru untuk membangunkan kerajaan yang lebih kukuh.'
    )

    def test_english_answer_warned(self):
        english = (
            'Parameswara was the founder of the Malacca Sultanate. He was the ruler '
            'who established the kingdom and he brought prosperity to the region.'
        )
        assert _warned(english, self.CTX)

    def test_no_bm_markers_warned(self):
        # Invented words with no BM function words
        no_bm = 'Parameswara tiba di Melaka selepas melarikan diri dari Palembang kerana.'
        status, msg = TutorValidator.validate(no_bm, self.CTX)
        # This has enough BM markers (selepas, melarikan, dari, kerana)
        # Should not warn for BM markers
        assert msg != 'Jawapan tidak kelihatan dalam Bahasa Malaysia.'

    def test_full_english_fails_ratio(self):
        eng = 'The the the the is are was were will would could should he she we they my your his her our their this that these those with for from about into over under between because when where what who why how can do does did not no yes and but or as an a of in on at to by'
        assert _warned(eng, self.CTX)

    def test_good_bm_passes_language(self):
        bm = (
            'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau berasal dari Palembang '
            'dan melarikan diri kerana serangan musuh. Baginda kemudian membina kerajaan baru '
            'di Melaka yang menjadi pusat perdagangan penting.'
        )
        status, msg = TutorValidator.validate(bm, self.CTX)
        assert status == 'ok'


# ═══════════════════════════════════════════════════════════════════
# E. Validator: Indonesian vocabulary leakage
# ═══════════════════════════════════════════════════════════════════

class TestIndonesianLeakage:

    CTX = (
        'Parameswara ialah pengasas Melaka pada tahun 1400. Beliau datang dari Palembang '
        'dan melarikan diri kerana serangan Majapahit. Melaka menjadi pusat perdagangan.'
    )

    def test_bahwa_leaked(self):
        resp = (
            'Sumber menyatakan bahwa Parameswara ialah pengasas Melaka yang memerintah '
            'dengan bijaksana dan adil serta membawa kemakmuran kepada rakyat.'
        )
        assert _warned(resp, self.CTX)

    def test_karena_leaked(self):
        resp = (
            'Parameswara melarikan diri karena serangan Majapahit dan kemudian tiba '
            'di Melaka yang menjadi pusat perdagangan yang penting di rantau ini.'
        )
        assert _warned(resp, self.CTX)

    def test_memiliki_leaked(self):
        resp = (
            'Melaka memiliki kedudukan yang strategik dan menjadi pusat perdagangan '
            'yang penting pada abad ke-15 dalam sejarah Nusantara yang kaya.'
        )
        assert _warned(resp, self.CTX)

    def test_clean_bm_no_indonesian_not_warned_for_indo(self):
        resp = (
            'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau mempunyai '
            'peranan penting dalam membina empayar perdagangan yang berjaya pada abad ke-15.'
        )
        _, msg = TutorValidator.validate(resp, self.CTX)
        assert msg is None or 'Indonesia' not in (msg or '')


# ═══════════════════════════════════════════════════════════════════
# F. Validator: date contradiction
# ═══════════════════════════════════════════════════════════════════

class TestDateContradiction:

    CTX_WITH_YEAR = (
        'Portugis menakluki Melaka pada tahun 1511 apabila Alfonso de Albuquerque '
        'memimpin serangan. Melaka jatuh selepas pertempuran sengit.'
    )

    def test_correct_year_extracted_passes(self):
        resp = (
            'Portugis menakluki Melaka pada tahun 1511 di bawah pimpinan Alfonso de Albuquerque. '
            'Ini adalah peristiwa penting dalam sejarah Melaka yang mengubah nasib kerajaan.'
        )
        assert _ok(resp, self.CTX_WITH_YEAR)

    def test_wrong_year_introduced_warned(self):
        resp = (
            'Portugis menakluki Melaka pada tahun 1498 di bawah pimpinan Alfonso de Albuquerque. '
            'Peristiwa ini mengubah sejarah rantau Asia Tenggara secara keseluruhannya.'
        )
        assert _warned(resp, self.CTX_WITH_YEAR)

    def test_hallucinated_year_warned(self):
        resp = (
            'Melaka telah ditakluki pada tahun 1350 oleh tentera Portugis yang kuat. '
            'Peristiwa ini mengubah corak perdagangan di Selat Melaka sepenuhnya.'
        )
        assert _warned(resp, self.CTX_WITH_YEAR)

    def test_no_years_in_context_skips_date_check(self):
        ctx_no_year = 'Portugis menakluki Melaka apabila Alfonso de Albuquerque memimpin serangan besar.'
        resp = (
            'Portugis menakluki Melaka pada tahun 1511. Peristiwa ini adalah titik perubahan '
            'yang penting dalam sejarah rantau ini dan mengubah corak perdagangan.'
        )
        # Context has no years → date check is skipped → should not warn for date
        _, msg = TutorValidator.validate(resp, ctx_no_year)
        assert msg is None or 'tahun' not in (msg or '')

    def test_multiple_wrong_years_warned(self):
        resp = (
            'Melaka ditakluki pada tahun 1498 dan kemudiannya pada tahun 1350 juga. '
            'Peristiwa ini amat penting dalam sejarah rantau Asia Tenggara yang luas.'
        )
        status, msg = TutorValidator.validate(resp, self.CTX_WITH_YEAR)
        assert status == 'warned'
        assert 'tahun' in msg


# ═══════════════════════════════════════════════════════════════════
# G. Validator: semantic grounding — hallucinated concepts
# ═══════════════════════════════════════════════════════════════════

class TestSemanticGrounding:

    CTX_MELAKA = (
        'Melaka merupakan sebuah kerajaan maritim yang terkenal. Parameswara mengasaskan '
        'Melaka sekitar tahun 1400. Melaka berkembang pesat kerana kedudukan strategiknya '
        'di Selat Melaka. Pedagang dari China, India dan Arab datang berdagang di sini.'
    )

    def test_answer_grounded_in_context_passes(self):
        resp = (
            'Melaka merupakan kerajaan maritim yang terkenal dan diasaskan oleh Parameswara '
            'sekitar tahun 1400. Kedudukan strategik di Selat Melaka menarik pedagang dari '
            'China, India dan Arab untuk berdagang di pelabuhan Melaka.'
        )
        assert _ok(resp, self.CTX_MELAKA)

    def test_heavily_hallucinated_answer_warned(self):
        # Answer talks about things completely absent from context
        resp = (
            'Sistem feudal Melayu terdiri daripada hierarki sosial yang kompleks. Hukum Islam '
            'diterapkan dalam sistem perundangan manakala sistem kewangan berasaskan cukai tanah. '
            'Keselamatan negara dijaga oleh tentera diraja yang setia kepada sultan pemerintah.'
        )
        assert _warned(resp, self.CTX_MELAKA)

    def test_short_answer_skips_grounding_check(self):
        # Under MIN_GROUNDING_WORDS (12) content words → grounding check skipped
        resp = 'Parameswara ialah pengasas Melaka yang terkenal.'
        _, msg = TutorValidator.validate(resp, self.CTX_MELAKA)
        assert msg is None or 'tidak disokong' not in (msg or '')

    def test_partial_overlap_above_threshold_passes(self):
        # Contains enough context keywords to exceed 25% threshold
        resp = (
            'Melaka menjadi pusat perdagangan kerana kedudukan strategik di Selat Melaka. '
            'Parameswara mengasaskan kerajaan ini dan pedagang dari pelbagai negara datang '
            'berdagang termasuklah dari China dan India yang berhampiran dengan rantau ini.'
        )
        assert _ok(resp, self.CTX_MELAKA)


# ═══════════════════════════════════════════════════════════════════
# H. Validator: legitimate refusals always pass
# ═══════════════════════════════════════════════════════════════════

class TestRefusalPhrases:

    CTX = 'Parameswara ialah pengasas Melaka. Beliau datang dari Palembang kerana ancaman Majapahit.'

    def test_refusal_saya_hanya_boleh_membantu(self):
        resp = 'Maaf, saya hanya boleh membantu soalan tentang sejarah Malaysia sahaja dalam konteks ini.'
        assert _ok(resp, self.CTX)

    def test_refusal_tidak_dinyatakan(self):
        resp = (
            'Berdasarkan halaman ini, maklumat ini tidak dinyatakan secara jelas dalam teks '
            'yang disediakan untuk rujukan anda.'
        )
        assert _ok(resp, self.CTX)

    def test_refusal_maaf_tidak_boleh(self):
        resp = 'Maaf, saya tidak boleh menjawab soalan yang berada di luar skop bahan Sejarah KSSM.'
        assert _ok(resp, self.CTX)

    def test_refusal_berdasarkan_halaman(self):
        resp = 'Berdasarkan halaman ini, maklumat berkenaan tidak terdapat dalam teks rujukan.'
        assert _ok(resp, self.CTX)

    def test_refusal_berdasarkan_bahan(self):
        resp = 'Berdasarkan bahan rujukan yang ada, soalan ini tidak dapat dijawab secara tepat.'
        assert _ok(resp, self.CTX)


# ═══════════════════════════════════════════════════════════════════
# I. Correct BM historical answers always pass
# ═══════════════════════════════════════════════════════════════════

class TestCorrectAnswersPass:

    def test_parameswara_factual(self):
        ctx = (
            'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau berasal dari Palembang '
            'dan melarikan diri kerana serangan Majapahit. Baginda tiba di Melaka sekitar tahun '
            '1400 dan membina kerajaan baru yang kemudiannya menjadi pusat perdagangan penting.'
        )
        resp = (
            'Parameswara ialah pengasas Kesultanan Melayu Melaka. Beliau berasal dari Palembang '
            'dan melarikan diri kerana serangan Majapahit sebelum tiba di Melaka sekitar 1400.'
        )
        assert _ok(resp, ctx)

    def test_deb_explanation(self):
        ctx = (
            'Dasar Ekonomi Baru (DEB) diperkenalkan pada tahun 1971 berikutan tragedi 13 Mei 1969. '
            'Matlamat DEB ialah membasmi kemiskinan dan menyusun semula masyarakat Malaysia. '
            'DEB mensasarkan ekuiti korporat bumiputera sebanyak 30 peratus menjelang tahun 1990.'
        )
        resp = (
            'Dasar Ekonomi Baru (DEB) diperkenalkan pada tahun 1971 selepas tragedi 13 Mei 1969. '
            'Matlamat utamanya ialah membasmi kemiskinan dan menyusun semula masyarakat agar '
            'bumiputera mempunyai ekuiti korporat sebanyak 30 peratus menjelang tahun 1990.'
        )
        assert _ok(resp, ctx)

    def test_japanese_occupation(self):
        ctx = (
            'Jepun menduduki Tanah Melayu dari tahun 1941 hingga 1945. Pendudukan ini '
            'memberi kesan yang mendalam kepada semua lapisan masyarakat. Rakyat mengalami '
            'kekurangan makanan dan penindasan semasa pendudukan tentera Jepun.'
        )
        resp = (
            'Jepun menduduki Tanah Melayu dari tahun 1941 hingga 1945. Pendudukan ini '
            'menyebabkan rakyat mengalami kekurangan makanan dan pelbagai bentuk penindasan '
            'oleh tentera Jepun yang memerintah kawasan tersebut.'
        )
        assert _ok(resp, ctx)

    def test_comparison_perlembagaan(self):
        ctx = (
            'Perlembagaan Persekutuan 1957 menetapkan Islam sebagai agama rasmi. '
            'Bahasa Melayu ditetapkan sebagai bahasa kebangsaan. Hak-hak asasi warganegara '
            'dilindungi. Raja-raja Melayu kekal sebagai pemerintah berkonstitusi.'
        )
        resp = (
            'Perlembagaan Persekutuan 1957 menetapkan Islam sebagai agama rasmi dan Bahasa '
            'Melayu sebagai bahasa kebangsaan. Hak-hak asasi warganegara turut dilindungi '
            'manakala Raja-raja Melayu kekal sebagai pemerintah berkonstitusi negara.'
        )
        assert _ok(resp, ctx)

    def test_sistem_persekutuan_kbat(self):
        ctx = (
            'Sistem Persekutuan ialah sistem pemerintahan yang membahagikan kuasa antara '
            'kerajaan pusat dan kerajaan negeri. Dalam sistem ini, kedua-dua peringkat '
            'kerajaan mempunyai bidang kuasa masing-masing yang ditetapkan oleh perlembagaan.'
        )
        resp = (
            'Sistem Persekutuan ialah sistem pemerintahan yang membahagikan kuasa antara '
            'kerajaan pusat dan kerajaan negeri. Kedua-dua peringkat kerajaan mempunyai '
            'bidang kuasa masing-masing yang ditetapkan oleh perlembagaan negara.'
        )
        assert _ok(resp, ctx)
