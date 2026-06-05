"""
End-to-end grading flow test.

Tests the full lifecycle for one struktur question and one esei question:
  start_attempt → save_draft → submit_attempt → stream_grading → inspect result

Usage:
    cd backend/
    python test_grading_e2e.py
"""
import logging
import json

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ── Student responses ─────────────────────────────────────────────────────────

STRUKTUR_RESPONSE = """
Negara bangsa ialah sebuah negara yang mempunyai ciri-ciri tertentu yang membezakannya daripada
entiti politik lain. Terdapat beberapa ciri utama negara bangsa.

Pertama, negara bangsa mempunyai sempadan wilayah yang jelas dan diiktiraf oleh negara-negara lain.
Sempadan ini memisahkan negara daripada jiran-jirannya.

Kedua, negara bangsa mempunyai penduduk tetap yang mendiami wilayah tersebut dan menjadi
warganegara yang membayar cukai serta mematuhi undang-undang negara.

Ketiga, negara bangsa mempunyai kerajaan yang berdaulat dengan kuasa untuk membuat undang-undang
dan menguatkuasakannya ke atas semua rakyat.

Keempat, pengiktirafan antarabangsa adalah penting di mana negara lain mengakui kewujudan dan
kedaulatan negara tersebut melalui hubungan diplomatik.

Kelima, negara bangsa mempunyai identiti nasional yang dikongsi bersama oleh rakyat seperti
bahasa, budaya, dan sejarah yang sama.

Keenam, negara bangsa mempunyai pasukan tentera dan polis untuk mempertahankan sempadan dan
mengekalkan keamanan dalam negeri daripada ancaman musuh.
"""

ESEI_RESPONSE = """
Negara bangsa merupakan konsep penting dalam sejarah pembinaan negara moden. Ciri-ciri negara
bangsa yang terdapat dalam kerajaan-kerajaan Melayu awal menunjukkan bahawa masyarakat Melayu
telah mempunyai asas pembinaan negara yang kukuh sejak zaman dahulu kala.

Kerajaan Melayu awal seperti Kerajaan Melayu Melaka telah menunjukkan ciri-ciri negara bangsa
yang jelas. Pertama, dari segi wilayah, Melaka mempunyai sempadan yang jelas dan diiktiraf oleh
kerajaan-kerajaan jiran. Kawasan pengaruh Melaka merangkumi seluruh Semenanjung Tanah Melayu dan
sebahagian kepulauan Nusantara.

Dari segi pemerintahan, Melaka mempunyai sistem kerajaan yang tersusun dengan Sultan sebagai
pemegang tertinggi kuasa. Pembesar-pembesar seperti Bendahara, Temenggung, dan Laksamana
membantu Sultan dalam pentadbiran negara. Sistem ini menunjukkan ciri-ciri kerajaan moden yang
teratur dan sistematik.

Identiti kebangsaan juga jelas dalam masyarakat Melayu Melaka. Bahasa Melayu digunakan sebagai
bahasa perantaraan dalam perdagangan dan diplomatik, manakala Islam menjadi agama rasmi yang
menyatukan rakyat. Adat istiadat dan budaya Melayu menjadi asas identiti bersama.

Pengiktirafan antarabangsa juga wujud apabila China mengiktiraf Melaka sebagai rakan dagang yang
penting. Utusan-utusan dari China, India, dan Arab melawat Melaka menunjukkan kedudukan Melaka
sebagai sebuah negara yang diiktiraf di persada antarabangsa.

Kesimpulannya, ciri-ciri negara bangsa yang terdapat dalam kerajaan Melayu awal membuktikan
bahawa masyarakat Melayu telah mempunyai asas pembinaan negara yang kuat jauh sebelum zaman
penjajahan. Warisan ini menjadi teras kepada pembentukan Malaysia moden yang berdaulat dan
diiktiraf oleh masyarakat antarabangsa.
"""

ESEI_NOTE_FORM_RESPONSE = """
Ciri-ciri negara bangsa dalam kerajaan Melayu awal:
- Sempadan wilayah yang jelas
- Sistem pemerintahan beraja
• Sultan sebagai pemegang kuasa tertinggi
• Pembesar membantu pentadbiran
1. Identiti bersama: bahasa Melayu, Islam
2. Pengiktirafan antarabangsa dari China
3. Tentera dan pertahanan negara
(a) Laskar laut Melaka
(b) Angkatan darat untuk pertahanan sempadan
"""


# ── Main test ─────────────────────────────────────────────────────────────────

def run():
    from app import create_app
    from app.extensions import db
    from app.models import EssayQuestion, Student
    from app.services import EssayService
    from app.repositories import EssayRepository, StudentRepository

    app = create_app()
    with app.app_context():
        student = db.session.query(Student).first()
        if not student:
            log.error("No student found — register a user first.")
            return
        student_id = student.student_id
        log.info("Using student: %s (id=%d)", student.email, student_id)

        struktur_q = db.session.query(EssayQuestion).filter_by(question_type='struktur').first()
        esei_q     = db.session.query(EssayQuestion).filter_by(question_type='esei').first()

        if not struktur_q or not esei_q:
            log.error("Seed essay questions first (python seed_essays.py).")
            return

        results = []
        test_cases = [
            ("STRUKTUR (good answer)", struktur_q, STRUKTUR_RESPONSE, False),
            ("ESEI (good prose answer)", esei_q, ESEI_RESPONSE, False),
            ("ESEI (note-form — should be penalised)", esei_q, ESEI_NOTE_FORM_RESPONSE, True),
        ]

        for label, question, response, expect_note_form in test_cases:
            log.info("")
            log.info("=" * 60)
            log.info("TEST: %s", label)
            log.info("Q%d: %s", question.question_id, question.question_text[:80])
            log.info("Max marks: %d", question.max_marks)

            # 1. Start attempt (returns existing draft if one exists)
            attempt_dict = EssayService.start_attempt(student_id, question.question_id)
            attempt_id = attempt_dict['attemptId']
            log.info("Attempt started: id=%d", attempt_id)

            # 2. Save draft
            EssayService.save_draft(student_id, attempt_id, response)
            log.info("Draft saved (%d words)", len(response.split()))

            # 3. Submit
            EssayService.submit_attempt(student_id, attempt_id)
            log.info("Submitted.")

            # 4. Stream grading — consume the generator fully
            final = None
            for event in EssayService.stream_grading(student_id, attempt_id):
                evt = event.get('event', 'message')
                if evt == 'status':
                    log.info("  [status] %s", event.get('message', ''))
                elif evt == 'done':
                    final = event
                elif evt == 'error':
                    log.error("  [error] %s", event.get('message'))
                    break

            if not final:
                log.error("Grading did not complete — no 'done' event received.")
                results.append((label, False, "no done event"))
                continue

            # 5. Inspect result
            score     = final.get('score')
            max_score = final.get('maxScore')
            pct       = round(score / max_score * 100, 1) if score is not None and max_score else None
            is_note   = final.get('isNoteForm')
            aras      = final.get('arasLevel')
            feedback  = final.get('feedbackJson') or {}
            matched   = final.get('matchedNodes') or []

            log.info("")
            log.info("  Score       : %s / %s  (%s%%)", score, max_score, pct)
            log.info("  isNoteForm  : %s", is_note)
            if aras:
                log.info("  Aras level  : %s", aras)
            if matched:
                log.info("  Matched codes:")
                for n in matched:
                    mark = "✓" if n.get('matched') else "✗"
                    log.info("    %s %s  %s", mark, n['code'], n['text'][:50])
            strengths = feedback.get('strengths', [])
            improvements = feedback.get('improvements', [])
            log.info("  Strengths   : %d point(s)", len(strengths))
            for s in strengths[:2]:
                log.info("    • %s", s[:80])
            log.info("  Improvements: %d point(s)", len(improvements))
            for i in improvements[:2]:
                log.info("    △ %s", i[:80])

            # Assertions
            ok = True
            if score is None:
                log.error("  FAIL: score is None")
                ok = False
            if score is not None and (score < 0 or score > max_score):
                log.error("  FAIL: score %s out of range [0, %s]", score, max_score)
                ok = False
            if expect_note_form and not is_note:
                log.error("  FAIL: expected isNoteForm=True but got %s", is_note)
                ok = False
            if expect_note_form and score is not None and score > 4:
                log.error("  FAIL: note-form esei scored %s > 4 (cap not enforced)", score)
                ok = False
            if expect_note_form and aras is not None and aras > 2:
                log.error("  FAIL: note-form esei Aras=%s > 2 (cap not enforced)", aras)
                ok = False
            if not feedback.get('detailedFeedback'):
                log.error("  FAIL: no detailedFeedback in feedbackJson")
                ok = False

            if ok:
                log.info("  PASS ✓")
            results.append((label, ok, f"{score}/{max_score}"))

        # Summary
        log.info("")
        log.info("=" * 60)
        log.info("SUMMARY")
        log.info("=" * 60)
        passed = sum(1 for _, ok, _ in results if ok)
        for label, ok, detail in results:
            status = "PASS ✓" if ok else "FAIL ✗"
            log.info("  %s  |  %s  |  %s", status, label, detail)
        log.info("")
        log.info("%d / %d tests passed.", passed, len(results))


if __name__ == '__main__':
    run()
