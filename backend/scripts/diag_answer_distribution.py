"""
Diagnostic: correct_index distribution across all attempt_question rows.

Run from backend/: ./venv/bin/python scripts/diag_answer_distribution.py
"""
from app import create_app
from app.extensions import db


def main():
    app = create_app()
    with app.app_context():
        from app.models.attempt_question import AttemptQuestion
        from app.models.quiz_attempt import QuizAttempt
        from app.models.quiz import Quiz

        rows = (
            db.session.query(
                AttemptQuestion.correct_index,
                Quiz.form_level,
                Quiz.chapter_id,
            )
            .join(QuizAttempt, AttemptQuestion.attempt_id == QuizAttempt.attempt_id)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.quiz_id)
            .all()
        )

        total = len(rows)
        if total == 0:
            print("No attempt_question rows found. Have any quizzes been taken?")
            return

        print(f"\n{'='*60}")
        print(f"  CORRECT-INDEX DISTRIBUTION — {total} questions total")
        print(f"{'='*60}")

        # Overall distribution
        from collections import Counter
        overall = Counter(r.correct_index for r in rows)
        labels = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
        print("\n[Overall]")
        for idx in range(4):
            count = overall.get(idx, 0)
            pct = count / total * 100
            bar = '█' * int(pct / 2)
            print(f"  {labels[idx]} (idx {idx}): {count:4d}  ({pct:5.1f}%)  {bar}")

        # Expected for uniform: each 25%
        print(f"\n  Expected if uniform: {total//4} per option (~25%)")
        chi_sq = sum(
            ((overall.get(i, 0) - total/4) ** 2) / (total/4)
            for i in range(4)
        )
        print(f"  Chi-squared statistic: {chi_sq:.2f}  (df=3; critical @p=0.05: 7.82)")
        if chi_sq > 7.82:
            print("  *** DISTRIBUTION IS SIGNIFICANTLY NON-UNIFORM ***")
        else:
            print("  Distribution within acceptable range.")

        # Per-chapter breakdown
        chapter_data: dict[tuple, Counter] = {}
        for r in rows:
            key = (r.form_level, r.chapter_id)
            if key not in chapter_data:
                chapter_data[key] = Counter()
            chapter_data[key][r.correct_index] += 1

        print(f"\n[Per-Chapter breakdown]")
        print(f"  {'Chapter':<20} {'N':>4}  {'A':>5}  {'B':>5}  {'C':>5}  {'D':>5}  Dominant")
        print(f"  {'-'*20} {'-'*4}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*8}")
        for (form_level, chapter_id), counter in sorted(chapter_data.items()):
            n = sum(counter.values())
            a = counter.get(0, 0)
            b = counter.get(1, 0)
            c = counter.get(2, 0)
            d = counter.get(3, 0)
            dominant_idx = counter.most_common(1)[0][0]
            dominant_pct = counter.most_common(1)[0][1] / n * 100
            print(
                f"  F{form_level}-Bab{chapter_id:<16} {n:>4}"
                f"  {a/n*100:4.0f}%  {b/n*100:4.0f}%  {c/n*100:4.0f}%  {d/n*100:4.0f}%"
                f"  {labels[dominant_idx]} ({dominant_pct:.0f}%)"
            )

        print(f"\n{'='*60}")
        print("VERDICT:")
        a_pct = overall.get(0, 0) / total * 100
        if a_pct >= 60:
            print(f"  SEVERE BIAS — {a_pct:.1f}% of answers are option A.")
            print("  Root cause: prompt example shows correct_index=0 (A),")
            print("  LLM anchors on example and always places correct answer first.")
            print("  Fix required: shuffle options + update correct_index before storage.")
        elif a_pct >= 40:
            print(f"  MODERATE BIAS — {a_pct:.1f}% of answers are option A.")
            print("  Shuffling is strongly recommended.")
        else:
            print(f"  Distribution looks reasonable (A={a_pct:.1f}%).")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
