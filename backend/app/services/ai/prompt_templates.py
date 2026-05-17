"""
LangChain prompt templates for MCQ generation.

Bahasa Malaysia. Generates one question at a time so the streaming UX
works. The 'previous_questions' clause is critical — without it the LLM
keeps producing variations of the same question.
"""
from langchain_core.prompts import ChatPromptTemplate


# Topic types we cycle through to force diverse questions
QUESTION_ANGLES_BM = [
    "definisi konsep utama",
    "sebab atau punca peristiwa",
    "tarikh atau tempoh masa yang penting",
    "tokoh atau pemimpin yang terlibat",
    "kesan atau akibat peristiwa",
    "perjanjian, dokumen, atau perlembagaan",
    "lokasi atau tempat yang penting",
    "ciri-ciri atau kandungan utama",
    "perbandingan antara dua perkara",
    "kepentingan atau pengajaran daripada peristiwa",
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
  sehingga→sehingga(ok)/hingga, memberikan→memberi.
- JANGAN gunakan aksara bukan-Latin (Arab, Cina, Jawi, dll.).

═══════════════════════════════════
ANTI-HALUSINASI — PERATURAN KETAT
═══════════════════════════════════
1. SETIAP fakta dalam stem dan jawapan betul MESTI ada dalam teks rujukan.
2. JANGAN reka tarikh, nama, atau angka yang tidak disebut dalam teks.
3. Jika teks tidak mengandungi fakta yang cukup untuk angle ini, pilih fakta lain dari teks.
4. Penjelasan WAJIB menyebut FAKTA SPESIFIK dari teks (bukan penjelasan umum).

═══════════════════════════════════
KUALITI DISTRACTOR
═══════════════════════════════════
5. Empat (4) pilihan: satu betul, tiga distractor.
6. Distractor WAJIB dari kategori yang SAMA dengan jawapan betul:
   - Soalan tarikh → distractor mestilah tarikh lain (bukan nama atau tempat).
   - Soalan tokoh → distractor mestilah nama orang lain (bukan tarikh atau tempat).
   - Soalan sebab → distractor mestilah sebab/faktor lain (munasabah, bukan karut).
7. Distractor JANGAN terlalu jelas salah (seperti "Nabi Muhammad" untuk soalan sejarah Malaysia).
8. Distractor JANGAN terlalu mirip sehingga membingungkan (dua jawapan hampir sama).
9. Elakkan pilihan "Semua di atas" atau "Tiada yang betul".

═══════════════════════════════════
FORMAT OUTPUT — JSON SAHAJA
═══════════════════════════════════
Output HANYA JSON ini, tiada teks lain:
{{
  "stem": "Soalan dalam Bahasa Malaysia?",
  "options": ["Pilihan A", "Pilihan B", "Pilihan C", "Pilihan D"],
  "correct_index": 0,
  "explanation": "Penjelasan ringkas merujuk fakta spesifik dari teks."
}}

WAJIB gunakan key "correct_index" (integer 0-3). JANGAN "answer", "correct", "correctIndex".""",
    ),
    (
        "human",
        """TEKS RUJUKAN (KSSM Sejarah):
---
{context}
---

ANGLE UNTUK SOALAN INI: **{angle}**
(tumpukan soalan pada angle ini sahaja)

SOALAN YANG SUDAH DIJANA (JANGAN ULANG topik/fakta yang sama):
{previous_questions}

Jana SATU soalan MCQ baru berdasarkan FAKTA DALAM TEKS DI ATAS, dengan angle "{angle}".
Pastikan jawapan betul ada dalam teks. JSON sahaja, tiada teks lain.""",
    ),
])


def build_previous_questions_summary(previous_stems: list[str]) -> str:
    if not previous_stems:
        return "(tiada — ini soalan pertama)"
    return "\n".join(f"- {s}" for s in previous_stems)


def pick_angle(index: int) -> str:
    """Pick a question angle, cycling through the list."""
    return QUESTION_ANGLES_BM[index % len(QUESTION_ANGLES_BM)]