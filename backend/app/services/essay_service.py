"""
EssayService — SPM Sejarah Kertas 2 writing practice.

Two question types:
  'struktur' — Bahagian A, graded by F/H/C code matching (Mana-mana N×1m).
               Formatting penalty NEVER applied.
  'esei'     — Bahagian B part (c), graded holistically via Aras 1-4 rubric.
               Note-form detection applied; cap enforced in backend code.
"""
import json
import logging
import re
from datetime import datetime
from typing import Iterator, List, Optional

from openai import OpenAI

from ..extensions import db
from ..models import EssayQuestion, EssayAttempt
from ..repositories import (
    EssayRepository,
    TopicPageRepository,
    TopicChunkRepository,
    StudentRepository,
)
from ..utils.errors import NotFoundError, ForbiddenError, ValidationError
from .ai.llm_config import get_openai_api_key, get_openai_model, get_openai_timeout
from .ai.essay_validator import validate_package

logger = logging.getLogger(__name__)

# SPM Aras rubric — verbatim from the Kertas 2 marking scheme PDF
_ARAS_RUBRIC = """Aras 4 (7-8 markah): Pengetahuan dan pemahaman sangat jelas · Bukti/contoh sangat sesuai · Membuat inferens yang tepat · Jawapan yang sangat mendalam/terperinci · Komunikasi/pengolahan sangat menarik · Menunjukkan kematangan
Aras 3 (5-6 markah): Pengetahuan dan pemahaman sangat jelas · Bukti/contoh sangat sesuai · Membuat inferens · Jawapan mendalam · Komunikasi/pengolahan menarik
Aras 2 (3-4 markah): Pengetahuan dan pemahaman jelas · Jawapan kurang mendalam · Menyatakan hujah secara ringkas
Aras 1 (1-2 markah): Pengetahuan dan pemahaman terhad · Jawapan secara umum · Jawapan kurang mendalam · Menyatakan hujah secara ringkas"""

# Regex to detect note/bullet-form lines
_NOTE_FORM_RE = re.compile(r'^\s*([-•*]|\d+\.|[a-zA-Z]\)|\(\w\))\s')


def _detect_note_form(text: str) -> bool:
    lines = [l for l in text.split('\n') if l.strip()]
    if not lines:
        return False
    flagged = sum(1 for l in lines if _NOTE_FORM_RE.match(l))
    return (flagged / len(lines)) >= 0.30


def _get_client() -> OpenAI:
    return OpenAI(api_key=get_openai_api_key(), timeout=get_openai_timeout())


def _get_chapter_texts(form_level: int, chapter_id: int) -> List[str]:
    pages = TopicPageRepository.list_for_chapter(form_level, chapter_id)
    return [p.text_content for p in pages if p.text_content and p.text_content.strip()]


class EssayService:

    # =========================================================================
    # Read-side
    # =========================================================================

    @staticmethod
    def list_questions(
        student_id: int,
        form_level: Optional[int] = None,
        chapter_id: Optional[int] = None,
    ) -> List[dict]:
        questions = EssayRepository.list_questions(form_level, chapter_id)
        result = []
        for q in questions:
            d = q.to_summary_dict()
            best = EssayRepository.get_best_attempt(student_id, q.question_id)
            all_attempts = EssayRepository.list_for_student(student_id, q.question_id)
            d['bestScore'] = best.score if best else None
            d['bestMaxScore'] = best.max_score if best else None
            d['attemptCount'] = len([a for a in all_attempts if a.status == 'graded'])
            result.append(d)
        return result

    @staticmethod
    def get_question(question_id: int) -> EssayQuestion:
        q = EssayRepository.get_question(question_id)
        if not q:
            raise NotFoundError(f'Essay question {question_id} not found.')
        return q

    @staticmethod
    def get_attempt(student_id: int, attempt_id: int) -> dict:
        attempt = EssayService._fetch_owned_attempt(student_id, attempt_id)
        d = attempt.to_dict()
        d['question'] = attempt.question.to_dict() if attempt.question else None
        return d

    @staticmethod
    def list_my_attempts(
        student_id: int, question_id: Optional[int] = None
    ) -> List[dict]:
        attempts = EssayRepository.list_for_student(student_id, question_id)
        return [a.to_summary_dict() for a in attempts]

    # =========================================================================
    # Attempt lifecycle
    # =========================================================================

    @staticmethod
    def start_attempt(student_id: int, question_id: int) -> dict:
        q = EssayService.get_question(question_id)
        existing = EssayRepository.find_draft(student_id, question_id)
        if existing:
            d = existing.to_dict()
            d['question'] = q.to_dict()
            return d
        attempt = EssayRepository.create_attempt(student_id, question_id)
        StudentRepository.commit()
        d = attempt.to_dict()
        d['question'] = q.to_dict()
        return d

    @staticmethod
    def save_draft(student_id: int, attempt_id: int, response_text: str) -> dict:
        attempt = EssayService._fetch_owned_attempt(student_id, attempt_id)
        if attempt.status != 'draft':
            raise ValidationError(errors={'status': 'Only draft attempts can be edited.'})
        EssayRepository.update_draft(attempt, response_text)
        StudentRepository.commit()
        return attempt.to_summary_dict()

    @staticmethod
    def submit_attempt(student_id: int, attempt_id: int) -> dict:
        attempt = EssayService._fetch_owned_attempt(student_id, attempt_id)
        if attempt.status not in ('draft',):
            raise ValidationError(errors={'status': 'Attempt already submitted or graded.'})
        if not (attempt.response_text or '').strip():
            raise ValidationError(errors={'responseText': 'Cannot submit an empty response.'})
        attempt.status = 'submitted'
        attempt.submitted_at = datetime.utcnow()
        attempt.grading_status = 'grading'
        StudentRepository.commit()
        return attempt.to_summary_dict()

    # =========================================================================
    # SSE grading stream
    # =========================================================================

    @staticmethod
    def stream_grading(student_id: int, attempt_id: int) -> Iterator[dict]:
        attempt = EssayService._fetch_owned_attempt(student_id, attempt_id)

        if attempt.grading_status == 'done':
            d = attempt.to_dict()
            d['question'] = attempt.question.to_dict() if attempt.question else None
            yield {'event': 'done', **d}
            return

        if attempt.grading_status == 'failed':
            yield {'event': 'error', 'message': 'Grading failed. Please try submitting again.'}
            return

        if attempt.grading_status not in ('grading', 'pending'):
            yield {'event': 'error', 'message': 'Attempt is not ready for grading.'}
            return

        if not (attempt.response_text or '').strip():
            yield {'event': 'error', 'message': 'No response text to grade.'}
            return

        question = attempt.question
        if not question:
            yield {'event': 'error', 'message': 'Associated question not found.'}
            return

        yield {'event': 'status', 'message': 'Checking response format...'}

        # --- Formatting check (esei only) ---
        note_form: Optional[bool] = None
        if question.question_type == 'esei':
            note_form = _detect_note_form(attempt.response_text)
        # For struktur: note_form stays None — formatting penalty never applied

        yield {'event': 'status', 'message': 'Marking your answer...'}

        try:
            if question.question_type == 'struktur':
                result = EssayService._grade_struktur(question, attempt.response_text)
            else:
                result = EssayService._grade_esei(question, attempt.response_text, note_form)
        except Exception as exc:
            logger.exception('Essay grading failed for attempt %s', attempt_id)
            EssayRepository.set_grading_status(attempt, 'failed')
            StudentRepository.commit()
            yield {'event': 'error', 'message': f'Grading error: {exc}'}
            return

        # Backend-enforced score bounds (overrides LLM)
        score = float(result.get('score', 0))
        max_score = question.max_marks

        if question.question_type == 'struktur':
            matched = result.get('matchedNodes', [])
            matched_count = sum(1 for n in matched if _count_all_matched(n))
            score = min(matched_count, max_score)
        else:
            aras = int(result.get('arasLevel', 1))
            if note_form:
                aras = min(aras, 2)
                score = min(score, 4.0)
            score = float(result.get('score', score))
            score = max(1.0, min(score, float(max_score)))

        aras_level = result.get('arasLevel') if question.question_type == 'esei' else None
        if aras_level is not None and note_form:
            aras_level = min(int(aras_level), 2)

        EssayRepository.finalize_grading(
            attempt=attempt,
            score=score,
            max_score=max_score,
            grading_status='done',
            is_note_form=note_form,
            aras_level=aras_level,
            matched_codes_json=result.get('matchedNodes') if question.question_type == 'struktur' else None,
            feedback_json={
                'strengths': result.get('strengths', []),
                'improvements': result.get('improvements', []),
                'detailedFeedback': result.get('detailedFeedback', ''),
                'arasDescriptorScores': result.get('arasDescriptorScores'),
                'arasReasoning': result.get('arasReasoning'),
            },
        )
        StudentRepository.commit()

        d = attempt.to_dict()
        d['question'] = question.to_dict()
        yield {'event': 'done', **d}

    # =========================================================================
    # LLM grading helpers
    # =========================================================================

    @staticmethod
    def _grade_struktur(question: EssayQuestion, response_text: str) -> dict:
        scheme = question.marking_scheme_json
        prompt = f"""Anda adalah pemeriksa SPM Sejarah yang berpengalaman.
Markah soalan ini menggunakan skema F/H/C kod dengan peraturan "Mana-mana {question.max_marks}×1 markah".

Soalan: {question.question_text} [{question.max_marks} markah]

Skema Pemarkahan (pokok F/H/C):
{json.dumps(scheme, ensure_ascii=False, indent=2)}

Jawapan Pelajar:
{response_text}

Arahan:
1. Baca setiap nod dalam pokok skema pemarkahan.
2. Tentukan sama ada pelajar telah menyebut atau menghuraikan konsep tersebut.
3. Jika ya, petik bukti daripada jawapan pelajar.
4. Kembalikan JSON SAHAJA (tanpa teks lain):

{{
  "matchedNodes": [
    {{"code": "F1", "type": "F", "text": "...", "matched": true, "evidence": "petikan dari jawapan", "children": [...]}},
    {{"code": "H1a", "type": "H", "text": "...", "matched": false, "evidence": null, "children": []}}
  ],
  "score": <integer>,
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "detailedFeedback": "..."
}}

Penting: Kembalikan SEMUA nod dari skema dalam matchedNodes, termasuk yang tidak dipadankan.
Sertakan nod children dalam struktur hierarki yang sama.
Nilai "score" anda akan DIABAIKAN — sistem akan mengira sendiri berdasarkan nod yang dipadankan."""

        client = _get_client()
        response = client.chat.completions.create(
            model=get_openai_model(),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.1,
            response_format={'type': 'json_object'},
        )
        return json.loads(response.choices[0].message.content)

    @staticmethod
    def _grade_esei(
        question: EssayQuestion,
        response_text: str,
        note_form: bool,
    ) -> dict:
        scheme = question.marking_scheme_json
        reference_points = scheme.get('referencePoints', [])
        ref_text = '\n'.join(f'- {p}' for p in reference_points) if reference_points else '(tiada)'

        note_form_warning = ''
        if note_form:
            note_form_warning = (
                '\n\nPERINGATAN PENTING: Pelajar ini menjawab dalam bentuk nota/poin (bullet points '
                'atau senarai bernombor). Ini bermakna Komunikasi/Pengolahan TIDAK BOLEH dinilai '
                'sebagai "menarik" atau "sangat menarik". Had markah maksimum ialah Aras 2 (4 markah).'
            )

        prompt = f"""Anda adalah pemeriksa SPM Sejarah yang berpengalaman menilai soalan ulasan (KBAT).

Soalan: {question.question_text} [8 markah]{note_form_warning}

Isi Kandungan Rujukan (daripada skema pemarkahan rasmi — gunakan sebagai panduan pengetahuan, BUKAN senarai semak):
{ref_text}

Rubrik Aras Rasmi SPM Sejarah Kertas 2:
{_ARAS_RUBRIC}

Jawapan Pelajar:
{response_text}

Arahan:
1. Nilai jawapan pelajar berdasarkan KEENAM-ENAM kriteria Aras.
2. Tentukan Aras (1-4) dan markah spesifik dalam julat aras tersebut.
3. Jelaskan sebab setiap kriteria dinilai begitu.
4. Kembalikan JSON SAHAJA (tanpa teks lain):

{{
  "arasLevel": <1-4>,
  "score": <markah spesifik dalam julat aras>,
  "arasDescriptorScores": {{
    "pengetahuan_pemahaman": "sangat jelas | jelas | terhad",
    "bukti_contoh": "sangat sesuai | sesuai | kurang | tiada",
    "membuat_inferens": "tepat | ada | tiada",
    "kedalaman_jawapan": "sangat mendalam | mendalam | kurang mendalam | umum",
    "komunikasi_pengolahan": "sangat menarik | menarik | ringkas",
    "kematangan": true
  }},
  "arasReasoning": "Penjelasan ringkas mengapa Aras ini dipilih...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "detailedFeedback": "Maklum balas terperinci seperti laporan pemeriksa..."
}}"""

        client = _get_client()
        response = client.chat.completions.create(
            model=get_openai_model(),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            response_format={'type': 'json_object'},
        )
        return json.loads(response.choices[0].message.content)

    # =========================================================================
    # Question generation package (used by seed script)
    # =========================================================================

    @staticmethod
    def generate_question_package(
        form_level: int,
        chapter_id: int,
        question_type: str,
        max_marks: int,
        sub_question: Optional[str] = None,
        difficulty: str = 'medium',
        max_retries: int = 3,
    ) -> EssayQuestion:
        from ..repositories import EssayRepository as ER

        chapter_texts = _get_chapter_texts(form_level, chapter_id)
        if not chapter_texts:
            raise ValueError(
                f'No topic text available for Form {form_level} Chapter {chapter_id}. '
                f'Has the PDF been ingested?'
            )
        context = '\n\n'.join(chapter_texts[:8])[:6000]

        existing = ER.list_questions_for_chapter(form_level, chapter_id)
        existing_dicts = [{'questionText': q.question_text} for q in existing]

        last_reason = ''
        for attempt_num in range(1, max_retries + 1):
            try:
                pkg = EssayService._call_generation_llm(
                    context, question_type, max_marks, last_reason
                )
                pkg['questionType'] = question_type
                pkg['maxMarks'] = max_marks

                ok, reason = validate_package(pkg, chapter_texts, existing_dicts)
                if not ok:
                    logger.warning(
                        'Essay generation attempt %d/%d failed validation for '
                        'F%d-C%d %s: %s',
                        attempt_num, max_retries, form_level, chapter_id, question_type, reason,
                    )
                    last_reason = reason
                    continue

                eq = ER.create_question(
                    question_text=pkg['questionText'],
                    question_type=question_type,
                    form_level=form_level,
                    chapter_id=chapter_id,
                    max_marks=max_marks,
                    marking_scheme_json=pkg['markingSchemeJson'],
                    model_answer=pkg['modelAnswer'],
                    sub_question=sub_question,
                    difficulty=difficulty,
                )
                StudentRepository.commit()
                return eq

            except Exception as exc:
                logger.exception(
                    'Essay generation attempt %d/%d raised exception: %s',
                    attempt_num, max_retries, exc,
                )
                last_reason = str(exc)

        raise RuntimeError(
            f'Failed to generate a valid essay question for '
            f'F{form_level}-C{chapter_id} {question_type} after {max_retries} attempts. '
            f'Last reason: {last_reason}'
        )

    @staticmethod
    def _call_generation_llm(
        context: str,
        question_type: str,
        max_marks: int,
        retry_feedback: str = '',
    ) -> dict:
        type_instructions = {
            'struktur': (
                f'Bahagian A Soalan Struktur — soalan faktual dengan {max_marks} markah. '
                f'Gunakan format "Mana-mana {max_marks}×1 markah". '
                f'Skema pemarkahan mestilah pokok F/H/C dengan ≥{max_marks + 2} nod. '
                f'Soalan harus memerlukan pelajar menyenaraikan DAN menghuraikan fakta sejarah. '
                f'Contoh kata kerja soalan: Jelaskan, Huraikan, Terangkan.'
            ),
            'esei': (
                f'Bahagian B Soalan Ulasan (KBAT) — 8 markah, dinilai secara holistik Aras 1-4. '
                f'Soalan mesti memerlukan ANALISIS dan PENILAIAN (bukan sekadar fakta). '
                f'Contoh kata kerja: Bincangkan, Ulaskan, Nilaikan, Buktikan. '
                f'referencePoints: senarai 6-10 isi penting yang patut ada dalam jawapan cemerlang.'
            ),
        }[question_type]

        retry_note = (
            f'\n\nPEMBETULAN DIPERLUKAN (percubaan sebelum ini ditolak): {retry_feedback}'
            if retry_feedback else ''
        )

        prompt = f"""Anda adalah pembina soalan SPM Sejarah Kertas 2 yang berpengalaman.
Jana SATU pakej soalan lengkap berdasarkan teks kandungan berikut.

Kandungan Bab:
{context}

Jenis Soalan: {type_instructions}{retry_note}

Kembalikan JSON SAHAJA dalam format berikut:

Untuk soalan struktur:
{{
  "questionText": "Soalan dalam Bahasa Malaysia...",
  "markingSchemeJson": {{
    "maxMarks": {max_marks},
    "nodes": [
      {{
        "code": "F1",
        "type": "F",
        "text": "Fakta utama pertama",
        "children": [
          {{"code": "H1a", "type": "H", "text": "Huraian bagi F1", "children": []}},
          {{"code": "C1", "type": "C", "text": "Contoh spesifik", "children": []}}
        ]
      }},
      {{"code": "F2", "type": "F", "text": "Fakta utama kedua", "children": [...]}}
    ]
  }},
  "modelAnswer": "Jawapan model lengkap dalam prosa/poin yang jelas..."
}}

Untuk soalan esei:
{{
  "questionText": "Soalan KBAT dalam Bahasa Malaysia...",
  "markingSchemeJson": {{
    "maxMarks": 8,
    "nodes": [],
    "referencePoints": [
      "Isi penting 1",
      "Isi penting 2",
      ...
    ]
  }},
  "modelAnswer": "Jawapan model dalam bentuk karangan berterusan (prosa), minimum 200 patah perkataan..."
}}

Pastikan: soalan dalam Bahasa Malaysia, kandungan berkaitan dengan teks bab yang diberikan."""

        client = _get_client()
        response = client.chat.completions.create(
            model=get_openai_model(),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7,
            response_format={'type': 'json_object'},
        )
        return json.loads(response.choices[0].message.content)

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _fetch_owned_attempt(student_id: int, attempt_id: int) -> EssayAttempt:
        attempt = EssayRepository.get_attempt(attempt_id)
        if not attempt:
            raise NotFoundError(f'Essay attempt {attempt_id} not found.')
        if attempt.student_id != student_id:
            raise ForbiddenError('You do not own this attempt.')
        return attempt


def _count_all_matched(node: dict) -> int:
    """Count matched nodes recursively in the tree returned by the LLM."""
    count = 1 if node.get('matched') else 0
    for child in node.get('children', []):
        count += _count_all_matched(child)
    return count
