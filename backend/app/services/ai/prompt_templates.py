"""
LangChain prompt templates for MCQ generation.

Bahasa Malaysia. Generates one question at a time so the streaming UX works.

ANGLE DESIGN — three cognitive tiers (3-5-3 split across 11 angles):
  Recall (3):      factual retrieval — who, when, where, what
  Application (5): inference from text — why, what-resulted, how-connected,
                   plus Roman Numeral multi-statement format
  HOTS (3):        higher-order — significance, comparison, policy/response

Phase 1 changes:
  - Application/HOTS angle instructions strengthened with explicit anti-recall
    guards to reduce the observed 55% Recall bias (target: ~35%).
  - Angle 10 added: Roman Numeral multi-statement format (application tier),
    a genuine SPM Sejarah Paper 1 archetype absent from the prior corpus.
  - System prompt gains a cognitive-tier compliance section.
"""
import random
from langchain_core.prompts import ChatPromptTemplate


# ── Angle definitions ──────────────────────────────────────────────────────
# Each entry: (short_name, question_directive, cognitive_tier)
QUESTION_ANGLES_BM = [
    # ── Recall tier ──────────────────────────────────────────────────────
    (
        "tokoh atau pemimpin yang terlibat",
        "Jana soalan SIAPAKAH — nama tokoh, pemimpin, atau individu yang melakukan sesuatu "
        "dalam teks. Contoh bentuk: 'Siapakah pemimpin yang...' atau 'Siapakah yang pertama kali...'",
        "recall",
    ),
    (
        "tarikh, tempat, atau angka khusus",
        "Jana soalan BILA atau DI MANA — tarikh, tahun, tempat, atau angka spesifik dari teks. "
        "Pilihan jawapan MESTI dari kategori yang sama (semua tarikh ATAU semua tempat, bukan campuran).",
        "recall",
    ),
    (
        "ciri-ciri atau kandungan utama sesuatu perkara",
        "Jana soalan APAKAH KANDUNGAN atau APAKAH CIRI — komponen, isi, atau ciri-ciri penting "
        "sesuatu sistem, perjanjian, atau peristiwa dalam teks.",
        "recall",
    ),
    # ── Application tier ─────────────────────────────────────────────────
    (
        "sebab atau punca peristiwa berlaku",
        "Jana soalan MENGAPA atau APAKAH FAKTOR — sebab KHUSUS yang mendorong sesuatu peristiwa berlaku. "
        "Soalan MESTI memerlukan pelajar MEMAHAMI hubungan sebab-akibat, bukan sekadar mengingat fakta terus. "
        "JANGAN tanya nama, tarikh, atau fakta terus apabila angle ini dipilih. "
        "Distractor mestilah sebab/faktor lain yang munasabah tetapi TIDAK TEPAT untuk peristiwa tersebut.",
        "application",
    ),
    (
        "kesan atau akibat sesuatu peristiwa",
        "Jana soalan APAKAH KESAN atau APAKAH AKIBAT — natijah atau perubahan SPESIFIK selepas peristiwa. "
        "Soalan mesti memerlukan pelajar memahami APA yang berubah akibat peristiwa, bukan sekadar mengingat. "
        "JANGAN tanya soalan fakta mudah seperti nama atau tarikh walaupun menggunakan perkataan 'kesan'. "
        "Distractor mestilah kesan/akibat lain yang munasabah tetapi TIDAK TEPAT atau berlaku pada konteks berbeza.",
        "application",
    ),
    (
        "peranan atau sumbangan tokoh atau kumpulan",
        "Jana soalan APAKAH PERANAN atau APAKAH SUMBANGAN — tanya APA yang dilakukan tokoh/kumpulan "
        "dan BAGAIMANA tindakan itu mempengaruhi peristiwa sejarah. "
        "JANGAN tanya siapakah tokoh atau pada tahun berapa — fokus kepada TINDAKAN dan IMPAKNYA. "
        "Distractor mestilah peranan/sumbangan lain yang kelihatan munasabah tetapi tidak tepat.",
        "application",
    ),
    (
        "hubungan atau kaitan antara dua peristiwa atau perkara",
        "Jana soalan APAKAH HUBUNGAN atau BAGAIMANA KAITAN — hubungan langsung antara dua peristiwa/tokoh. "
        "Soalan MESTI menyebut DUA entiti dan memerlukan pelajar MENGANALISIS kaitan antara keduanya. "
        "JANGAN tanya soalan fakta terus tentang satu peristiwa sahaja. "
        "Distractor mestilah hubungan yang salah, terbalik, atau tidak relevan antara dua entiti.",
        "application",
    ),
    (
        "soalan pelbagai pernyataan (Roman Numeral)",
        "Jana soalan Roman Numeral SPM dengan 3 pernyataan benar/salah. "
        "FORMAT STEM WAJIB — stem mesti dalam bentuk ini tepat:\n"
        "\"I [pernyataan ringkas ≤12 patah perkataan]\n"
        "II [pernyataan ringkas ≤12 patah perkataan]\n"
        "III [pernyataan ringkas ≤12 patah perkataan]\n\n"
        "Antara pernyataan di atas, yang manakah BETUL?\"\n"
        "FORMAT PILIHAN WAJIB — pilihan mestilah subset Roman Numeral sahaja:\n"
        "  [\"I dan II sahaja\", \"I dan III sahaja\", \"II dan III sahaja\", \"I, II dan III\"]\n"
        "TEPAT 2 daripada 3 pernyataan mestilah BENAR (atau semua 3 jika correct_index ialah pilihan terakhir). "
        "Setiap pernyataan MESTI boleh disahkan dari teks rujukan. "
        "JANGAN campurkan dengan format MCQ biasa — pilihan MESTI berupa subset Roman Numeral.",
        "application",
    ),
    # ── HOTS tier ────────────────────────────────────────────────────────
    (
        "kepentingan atau signifikan sejarah peristiwa",
        "Jana soalan APAKAH KEPENTINGAN atau MENGAPA PENTING — nilai sejarah sesuatu peristiwa/tokoh. "
        "Soalan ini HOTS: pelajar MESTI MENILAI kepentingan, bukan sekadar mengingat nama atau tarikh. "
        "JANGAN tanya soalan fakta mudah walaupun menggunakan perkataan 'kepentingan'. "
        "Contoh BAIK: 'Apakah kepentingan Revolusi Amerika kepada perjuangan kemerdekaan di Asia?' "
        "Distractor mestilah kepentingan lain yang kelihatan munasabah tetapi kurang tepat atau lebih umum.",
        "hots",
    ),
    (
        "perbandingan antara dua perkara, tokoh, atau peristiwa",
        "Jana soalan APAKAH PERBEZAAN atau PERSAMAAN — bandingkan dua perkara/peristiwa dari aspek SPESIFIK. "
        "Soalan MESTI menyebut DUA entiti DAN aspek perbandingan (contoh: 'dari segi matlamat', 'dari segi punca'). "
        "JANGAN buat soalan yang boleh dijawab dengan hanya mengetahui satu peristiwa sahaja. "
        "Distractor mestilah perbezaan/persamaan yang salah, disongsang, atau tertukar antara dua entiti.",
        "hots",
    ),
    (
        "tindak balas, dasar, atau langkah yang diambil terhadap peristiwa",
        "Jana soalan APAKAH LANGKAH atau APAKAH TINDAK BALAS — dasar atau tindakan sebagai respons kepada peristiwa. "
        "Soalan MESTI memerlukan pelajar memahami MENGAPA langkah itu diperlukan dan APAKAH konteks cabarannya. "
        "JANGAN sekadar tanya 'Apakah langkah X?' tanpa memerlukan pemahaman tentang keperluan atau tujuannya. "
        "Distractor mestilah langkah lain yang salah, tidak bersesuaian, atau bertentangan dengan cabaran tersebut.",
        "hots",
    ),
]


MCQ_SINGLE_PROMPT_BM = ChatPromptTemplate.from_messages([
    (
        "system",
        """Anda ialah guru Sejarah SPM Malaysia (KSSM Tingkatan 4 & 5).
Jana SATU soalan aneka pilihan (MCQ) berdasarkan FAKTA dari teks rujukan.

═══════════════════════════════════
BAHASA — WAJIB BAHASA MALAYSIA
═══════════════════════════════════
- SEMUA teks: stem, pilihan, penjelasan — WAJIB dalam Bahasa Malaysia standard.
- DILARANG KERAS menggunakan perkataan bahasa Indonesia:
  kontribusi→sumbangan, pangeran→putera, Tiongkok→China,
  bahwa→bahawa, karena→kerana, memiliki→mempunyai,
  menyebutkan→menyatakan, dikarenakan→kerana,
  sehingga→hingga, memberikan→memberi,
  identitas→identiti, mengadopsi→menerima pakai, gelar→gelaran,
  kekuasaan→kuasa, peran→peranan, keunggulan→kelebihan, dimana→di mana.
- JANGAN gunakan aksara bukan-Latin (Arab, Cina, Jawi, dll.).

═══════════════════════════════════
ARAS KOGNITIF — IKUT ANGLE DENGAN TEPAT
═══════════════════════════════════
Apabila ANGLE adalah Application atau HOTS (sebab, kesan, peranan, hubungan, kepentingan, perbandingan, langkah, Roman Numeral):
- Soalan MESTI memerlukan PEMAHAMAN atau ANALISIS — BUKAN sekadar mengingat fakta terus.
- DILARANG tukar angle menjadi soalan fakta biasa (contoh: jika angle "kesan", JANGAN tanya "Apakah nama dokumen?").
- Jawapan betul mestilah memerlukan pelajar memahami hubungan, menilai kepentingan, atau menganalisis — bukan hanya mengingat.

═══════════════════════════════════
FORMAT SOALAN MCQ — WAJIB DIPATUHI
═══════════════════════════════════
- Soalan MESTI berakhir dengan tanda soal (?).
- DILARANG memulakan soalan dengan: Jelaskan, Huraikan, Bincangkan, Terangkan.
- DILARANG soalan terbuka yang memerlukan esei.
- Soalan perlu sesuai untuk format MCQ 4 pilihan.

═══════════════════════════════════
ANTI-HALUSINASI — PERATURAN KETAT
═══════════════════════════════════
1. SETIAP fakta dalam stem dan jawapan betul MESTI ada dalam teks rujukan.
2. JANGAN reka tarikh, nama, atau angka yang tidak disebut dalam teks.
3. Penjelasan WAJIB menyebut FAKTA SPESIFIK dari teks (bukan penjelasan umum).

═══════════════════════════════════
KUALITI DISTRACTOR — KRITIKAL
═══════════════════════════════════
4. Empat (4) pilihan: satu betul, tiga distractor.
5. Distractor WAJIB dari kategori yang SAMA dengan jawapan betul:
   - Soalan tarikh → distractor mestilah tarikh lain (bukan nama atau tempat).
   - Soalan tokoh → distractor mestilah nama orang lain (bukan tarikh atau tempat).
   - Soalan sebab → distractor mestilah sebab/faktor lain (munasabah, bukan karut).
   - Soalan kesan → distractor mestilah kesan/akibat lain (bukan sebab).
6. Distractor JANGAN terlalu jelas salah (contoh: "Nabi Muhammad" untuk soalan Malaysia moden).
7. Distractor JANGAN terlalu mirip sehingga membingungkan.
8. Elakkan pilihan "Semua di atas" atau "Tiada yang betul".
9. Pastikan semua pilihan HAMPIR SAMA PANJANG — elakkan pilihan yang jauh lebih pendek atau lebih panjang.
10. SELARI TATABAHASA — jika pilihan adalah frasa tindakan, SEMUA 4 pilihan MESTI bermula dengan kata kerja imbuhan meN- yang sama bentuknya:
    Contoh BETUL: ["Mengembangkan ekonomi", "Meningkatkan pendapatan", "Memajukan industri", "Mengurangkan kemiskinan"]
    Contoh SALAH: ["Mengembangkan ekonomi", "Pendapatan meningkat", "Industri dimajukan", "Mengurangkan kemiskinan"]
    Jika pilihan adalah nama, tarikh, atau tempat, peraturan ini tidak terpakai.

═══════════════════════════════════
FORMAT OUTPUT — JSON SAHAJA
═══════════════════════════════════
Output HANYA JSON ini, tiada teks lain:
{{
  "stem": "Apakah perbezaan utama antara Revolusi Amerika dan Revolusi Perancis dari segi matlamat?",
  "options": ["Amerika menuntut kemerdekaan; Perancis menuntut keadilan sosial", "Amerika menuntut keadilan sosial; Perancis menuntut kemerdekaan", "Kedua-dua revolusi mempunyai matlamat yang sama", "Amerika menuntut hak agama; Perancis menuntut hak ekonomi"],
  "correct_index": 0,
  "explanation": "Revolusi Amerika bertujuan membebaskan diri daripada penjajahan British, manakala Revolusi Perancis menuntut keadilan sosial dan kesamarataan dalam negara sendiri."
}}

Untuk soalan Roman Numeral, format stem adalah:
{{
  "stem": "I Amerika menentang cukai tanpa perwakilan British\\nII Revolusi Amerika tercetus pada tahun 1776\\nIII Thomas Jefferson memimpin tentera dalam pertempuran\\n\\nAntara pernyataan di atas, yang manakah BETUL?",
  "options": ["I dan II sahaja", "I dan III sahaja", "II dan III sahaja", "I, II dan III"],
  "correct_index": 0,
  "explanation": "I dan II adalah betul berdasarkan teks. III adalah salah kerana Thomas Jefferson menulis Perisytiharan Kemerdekaan, bukan memimpin tentera."
}}

WAJIB gunakan key "correct_index" (integer 0-3). JANGAN "answer", "correct", "correctIndex".
Pilihan MESTI kandungan sebenar — JANGAN tulis "Pilihan A", "Pilihan B", "A.", "B.", "C.", "D."
Pilihan JANGAN mengandungi label seperti "A.", "B.", "C.", "D." dalam teks pilihan.""",
    ),
    (
        "human",
        """TEKS RUJUKAN (KSSM Sejarah):
---
{context}
---

ANGLE UNTUK SOALAN INI: **{angle_name}**
ARAHAN KHUSUS: {angle_instruction}

SOALAN YANG SUDAH DIJANA (JANGAN ULANG topik/fakta yang sama):
{previous_questions}

Jana SATU soalan MCQ baru berdasarkan FAKTA DALAM TEKS DI ATAS, mengikut arahan khusus di atas.
Pastikan jawapan betul ada dalam teks. JSON sahaja, tiada teks lain.""",
    ),
])


def build_previous_questions_summary(previous_stems: list[str]) -> str:
    if not previous_stems:
        return "(tiada — ini soalan pertama)"
    return "\n".join(f"- {s}" for s in previous_stems)


def pick_angle(index: int, angle_order: list[int] | None = None) -> tuple[str, str, str]:
    """Return (angle_name, angle_instruction, tier) for this question index.

    Args:
        index: question index within the current generation run (0-based).
        angle_order: optional pre-shuffled list of angle indices to use instead
                     of the default sequential order.  Length must be >= index+1.

    Returns a (name, instruction, tier) triple.
    """
    if angle_order is not None:
        idx = angle_order[index % len(angle_order)]
    else:
        idx = index % len(QUESTION_ANGLES_BM)
    return QUESTION_ANGLES_BM[idx]


_DIFFICULTY_ANGLE_POOLS: dict[str, list[int]] = {
    # Recall tier only — who/when/what/content (SPM lower-order)
    'easy': [0, 1, 2],
    # All tiers — current default behaviour
    'medium': list(range(len(QUESTION_ANGLES_BM))),
    # Application + HOTS only — why/effect/role/comparison/significance (SPM KBAT)
    'hard': list(range(3, len(QUESTION_ANGLES_BM))),
}


def make_shuffled_angle_order(
    n_slots: int, difficulty: str = 'medium'
) -> list[int]:
    """Return a shuffled list of angle indices long enough for n_slots outer attempts.

    Called with the full budget (num_questions × _BUDGET_MULTIPLIER), not just
    num_questions, so every outer retry gets a fresh angle without repetition starvation.

    Args:
        n_slots:    Total budget slots (num_questions × multiplier).
        difficulty: 'easy' | 'medium' | 'hard' — filters which angles are eligible.
    """
    pool = _DIFFICULTY_ANGLE_POOLS.get(difficulty, _DIFFICULTY_ANGLE_POOLS['medium'])

    deck = pool[:]
    random.shuffle(deck)

    if n_slots <= len(deck):
        return deck[:n_slots] + deck  # extra tail for modulo safety

    full_decks = (n_slots // len(deck)) + 1
    order = []
    for _ in range(full_decks):
        d = deck[:]
        random.shuffle(d)
        order.extend(d)
    return order
