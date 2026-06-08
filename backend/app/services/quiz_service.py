"""
QuizService — per-attempt question snapshots + AI streaming generation.

Step 5 changes:
  - start_attempt() creates an attempt but does NOT generate questions.
    Generation happens in stream_questions() via SSE.
  - Questions are stored in attempt_question, never on the Quiz itself.
  - submit/save/get logic is updated to use attempt_question.
"""
from typing import Iterator, List, Optional

from ..models import Quiz, QuizAttempt
from ..repositories import (
    QuizRepository,
    QuizAttemptRepository,
    AttemptQuestionRepository,
    TopicPageRepository,
    TopicRepository,
    LearningProgressRepository,
    StudentRepository,
)
from ..utils.errors import NotFoundError, ForbiddenError, ValidationError
from .ai import LlmQuestionGenerator
from .ai.quiz_difficulty_classifier import classify_difficulty

# Maximum pages to sample for quiz context (keeps context < generator's 8000-char cap
# while ensuring even coverage across the chapter, not just the first N pages)
_MAX_SAMPLE_PAGES = 12
_MAX_CONTEXT_CHARS = 7500

# Cycle-based history reset.
# After _CYCLE_SIZE submitted attempts on the same quiz, historical_stems
# resets to empty so the generator gets a clean slate.  Within a cycle only
# the _HISTORY_CAP most recent submitted attempts are used for dedup.
# Adjust _CYCLE_SIZE after real-world testing reveals where quality plateaus.
_CYCLE_SIZE = 10
_HISTORY_CAP = 2


def _stratified_context(pages: list) -> str:
    """Sample pages evenly across the chapter and join them into context.

    Avoids the bias of a plain truncation (which only shows the first pages).
    """
    filled = [p for p in pages if p.text_content and p.text_content.strip()]
    if not filled:
        return ''

    if len(filled) <= _MAX_SAMPLE_PAGES:
        sampled = filled
    else:
        step = len(filled) / _MAX_SAMPLE_PAGES
        sampled = [filled[int(i * step)] for i in range(_MAX_SAMPLE_PAGES)]

    parts = []
    total = 0
    for p in sampled:
        chunk = p.text_content[:1500]  # cap per page to ensure variety
        if total + len(chunk) > _MAX_CONTEXT_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)

    return '\n\n'.join(parts)


class QuizService:

    # ==================================================================
    # Read-side
    # ==================================================================

    @staticmethod
    def list_quizzes_for_student(
        student_id: int, form_level: Optional[int] = None
    ) -> List[dict]:
        quizzes = QuizRepository.list_all(form_level)
        if not quizzes:
            return []

        all_attempts = QuizAttemptRepository.list_for_student(student_id)
        by_quiz: dict[int, List[QuizAttempt]] = {}
        for a in all_attempts:
            by_quiz.setdefault(a.quiz_id, []).append(a)

        # Build chapter completion map for lock calculation.
        # Two queries regardless of quiz count: one for topic totals,
        # one for completed counts.  Both are indexed and fast.
        all_topics = TopicRepository.list_filtered(form_level=form_level)
        progress = LearningProgressRepository.get_by_student_id(student_id)
        completed_ids: set[int] = set()
        if progress:
            completed_ids = set(
                LearningProgressRepository.list_completed_topic_ids(progress.progress_id)
            )

        chapter_totals: dict[tuple, int] = {}
        chapter_completed: dict[tuple, int] = {}
        for t in all_topics:
            key = (t.form_level, t.chapter_id)
            chapter_totals[key] = chapter_totals.get(key, 0) + 1
            if t.topic_id in completed_ids:
                chapter_completed[key] = chapter_completed.get(key, 0) + 1

        def _is_locked(quiz: Quiz) -> bool:
            total = chapter_totals.get((quiz.form_level, quiz.chapter_id), 0)
            if total == 0:
                return True
            done = chapter_completed.get((quiz.form_level, quiz.chapter_id), 0)
            return done < total

        result = []
        for q in quizzes:
            attempts = by_quiz.get(q.quiz_id, [])
            submitted = [a for a in attempts if a.status == 'submitted']
            in_progress = next(
                (a for a in attempts if a.status == 'in_progress'), None
            )
            best = max(submitted, key=lambda a: (a.score or 0), default=None)

            d = q.to_summary_dict()
            submitted_count = len(submitted)
            resumable = (
                in_progress is not None and in_progress.generation_status == 'ready'
            )
            d['hasInProgressAttempt'] = resumable
            d['inProgressAttemptId'] = in_progress.attempt_id if resumable else None
            d['attemptCount'] = submitted_count
            d['bestScore'] = best.score if best else None
            d['bestPercentage'] = (
                round((best.score / best.max_score) * 100, 2)
                if best and best.max_score else None
            )
            d['cycleNumber'] = submitted_count // _CYCLE_SIZE
            d['attemptsInCycle'] = submitted_count % _CYCLE_SIZE
            d['cycleSize'] = _CYCLE_SIZE
            # A resumable in-progress attempt is never considered locked —
            # the student already started it and must be able to finish.
            d['isLocked'] = _is_locked(q) and not resumable
            result.append(d)
        return result

    # ==================================================================
    # Attempt lifecycle
    # ==================================================================

    @staticmethod
    def start_attempt(student_id: int, quiz_id: int) -> dict:
        """Resume in-progress attempt, OR create a new pending attempt.

        Question generation does NOT happen here — call stream_questions()
        after this to populate the questions via SSE.

        Student learning preferences (quizDifficulty, questionsPerQuiz) are
        resolved here and snapshotted onto the attempt so that a later preference
        change does not affect an already-started attempt.
        """
        quiz = QuizRepository.get(quiz_id)
        if not quiz:
            raise NotFoundError(f'Quiz {quiz_id} not found.')

        existing = QuizAttemptRepository.find_in_progress(student_id, quiz_id)
        if existing:
            if existing.generation_status == 'ready':
                # All questions generated, student mid-answering — resume.
                # Skip lock check: the attempt was already started, let them finish.
                return QuizService._attempt_to_dict(existing, include_questions=True)
            else:
                # Pending/generating/failed — broken partial attempt, delete and restart.
                QuizAttemptRepository.delete(existing)
                StudentRepository.commit()

        # Gate: only reaches here when creating a NEW attempt.
        QuizService._check_chapter_unlocked(student_id, quiz)

        student = StudentRepository.get_by_id(student_id)
        question_count = (
            student.questions_per_quiz
            if student and student.questions_per_quiz is not None
            else quiz.default_question_count
        )
        difficulty = (
            student.quiz_difficulty
            if student and student.quiz_difficulty is not None
            else quiz.difficulty or 'medium'
        )

        attempt = QuizAttemptRepository.create(
            student_id=student_id,
            quiz_id=quiz_id,
            target_question_count=question_count,
            difficulty_target=difficulty,
        )
        StudentRepository.commit()
        return QuizService._attempt_to_dict(attempt, include_questions=True)

    @staticmethod
    def stream_questions(
        student_id: int, attempt_id: int
    ) -> Iterator[dict]:
        """Yield questions one-by-one as they're generated by the LLM.

        Each yielded dict is a 'question' event for the frontend SSE handler.
        Final event is 'done' or 'error'.
        """
        attempt = QuizService._fetch_owned_attempt(student_id, attempt_id)

        # Prevent double-generation: if another stream is already running
        # for this attempt, stream the existing questions out and stop.
        if attempt.generation_status == 'generating':
            for q in attempt.attempt_questions:
                yield {'event': 'question', 'question': q.to_student_dict()}
            yield {
                'event': 'done',
                'total': len(attempt.attempt_questions),
                'target': attempt.target_question_count,
            }
            return


        if attempt.status == 'submitted':
            yield {'event': 'error', 'message': 'This attempt is already submitted.'}
            return
        if attempt.generation_status == 'ready':
            # Already generated — just stream the existing questions out
            for q in attempt.attempt_questions:
                yield {'event': 'question', 'question': q.to_student_dict()}
            yield {'event': 'done', 'total': len(attempt.attempt_questions), 'target': attempt.target_question_count}
            return

        existing_count = AttemptQuestionRepository.count_for_attempt(attempt_id)
        remaining = attempt.target_question_count - existing_count
        if remaining <= 0:
            yield {'event': 'done', 'total': existing_count, 'target': attempt.target_question_count}
            return

        # Build context from topic_page rows
        quiz = attempt.quiz
        pages = TopicPageRepository.list_for_chapter(quiz.form_level, quiz.chapter_id)

        if not pages:
            QuizAttemptRepository.set_generation_status(attempt, 'failed')
            StudentRepository.commit()
            yield {
                'event': 'error',
                'message': 'No KSSM source text available for this quiz scope. '
                           'Has the PDF been ingested?',
            }
            return

        context = _stratified_context(pages)

        # Cycle-aware historical stems.
        #
        # The generator compares every candidate question against historical_stems
        # to avoid near-duplicates across attempts.  Without a reset the list
        # grows indefinitely and the fixed budget is exhausted before 10 unique
        # questions can be produced.
        #
        # Strategy:
        #   - Only submitted attempts count (abandoned / failed ones are excluded).
        #   - Attempts are grouped into cycles of _CYCLE_SIZE (default 10).
        #   - At the start of a new cycle, historical_stems resets to [] so the
        #     generator sees a clean slate and can revisit the chapter's fact space.
        #   - Within a cycle, only the _HISTORY_CAP (2) most recent attempts are
        #     used — enough to block exact repeats without exhausting the budget.
        all_quiz_attempts = QuizAttemptRepository.list_for_student(student_id, quiz_id=quiz.quiz_id)
        submitted_attempts = [
            a for a in all_quiz_attempts
            if a.attempt_id != attempt_id and a.status == 'submitted'
        ]  # ordered newest-first by list_for_student

        total_prior = len(submitted_attempts)
        position_in_cycle = total_prior % _CYCLE_SIZE   # 0 → first attempt in a fresh cycle
        cycle_attempts = submitted_attempts[:position_in_cycle]  # only within current cycle
        recent_in_cycle = cycle_attempts[:_HISTORY_CAP]

        historical_stems = [
            pq.stem
            for prev in recent_in_cycle
            for pq in prev.attempt_questions
            if pq.stem
        ]

        QuizAttemptRepository.set_generation_status(attempt, 'generating')
        StudentRepository.commit()

        generator = LlmQuestionGenerator()
        order_offset = existing_count + 1
        produced = 0

        try:
            for gq in generator.generate_stream(
                context, remaining, language='bm', seen_stems=historical_stems,
                difficulty=attempt.difficulty_target or 'medium',
            ):
                aq = AttemptQuestionRepository.add(
                    attempt_id=attempt_id,
                    order_index=order_offset + produced,
                    stem=gq.stem,
                    options=gq.options,
                    correct_index=gq.correct_index,
                    explanation=gq.explanation,
                    points=gq.points,
                )
                StudentRepository.commit()
                produced += 1
                q_dict = aq.to_student_dict()
                q_dict['difficulty'] = gq.difficulty
                yield {'event': 'question', 'question': q_dict}
        except Exception as exc:
            QuizAttemptRepository.set_generation_status(attempt, 'failed')
            StudentRepository.commit()
            yield {'event': 'error', 'message': f'Generation failed: {exc}'}
            return

        # Mark ready (even if we got fewer than requested — partial success)
        if produced > 0:
            QuizAttemptRepository.set_generation_status(attempt, 'ready')
        else:
            QuizAttemptRepository.set_generation_status(attempt, 'failed')
        StudentRepository.commit()

        yield {
            'event': 'done',
            'total': existing_count + produced,
            'target': attempt.target_question_count,
        }

    @staticmethod
    def get_attempt(student_id: int, attempt_id: int) -> dict:
        attempt = QuizService._fetch_owned_attempt(student_id, attempt_id)
        return QuizService._attempt_to_dict(
            attempt,
            include_questions=True,
            include_review=(attempt.status == 'submitted'),
        )

    @staticmethod
    def save_answer(
        student_id: int,
        attempt_id: int,
        attempt_question_id: int,
        selected_index: Optional[int],
    ) -> dict:
        attempt = QuizService._fetch_owned_attempt(student_id, attempt_id)
        if attempt.status != 'in_progress':
            raise ForbiddenError('This attempt has been submitted already.')

        question = AttemptQuestionRepository.get(attempt_question_id)
        if not question or question.attempt_id != attempt_id:
            raise ValidationError(
                errors={'attemptQuestionId': 'Question does not belong to this attempt.'}
            )
        if selected_index is not None and not (0 <= selected_index <= 3):
            raise ValidationError(
                errors={'selectedIndex': 'Must be null or between 0 and 3.'}
            )

        ans = QuizAttemptRepository.upsert_answer(
            attempt_id, attempt_question_id, selected_index
        )
        StudentRepository.commit()
        return ans.to_dict()

    @staticmethod
    def submit_attempt(student_id: int, attempt_id: int) -> dict:
        attempt = QuizService._fetch_owned_attempt(student_id, attempt_id)
        if attempt.status == 'submitted':
            return QuizService._attempt_to_dict(
                attempt, include_questions=True, include_review=True
            )

        questions = attempt.attempt_questions
        if not questions:
            raise ValidationError(
                'Cannot submit an attempt with no generated questions.'
            )

        answers_by_qid = {
            a.attempt_question_id: a for a in QuizAttemptRepository.list_answers(attempt_id)
        }

        score = 0
        max_score = 0
        correct_count = 0

        for q in questions:
            max_score += q.points
            ans = answers_by_qid.get(q.attempt_question_id)
            if not ans:
                ans = QuizAttemptRepository.upsert_answer(
                    attempt_id, q.attempt_question_id, None
                )
            is_correct = ans.selected_index == q.correct_index
            ans.is_correct = is_correct
            if is_correct:
                score += q.points
                correct_count += 1

        QuizAttemptRepository.finalize(
            attempt, score=score, max_score=max_score,
            correct_count=correct_count, total_questions=len(questions),
        )
        StudentRepository.commit()
        return QuizService._attempt_to_dict(
            attempt, include_questions=True, include_review=True
        )

    @staticmethod
    def delete_attempt(student_id: int, attempt_id: int) -> None:
        attempt = QuizService._fetch_owned_attempt(student_id, attempt_id)
        if attempt.status == 'submitted':
            raise ForbiddenError('Cannot delete a submitted attempt.')
        QuizAttemptRepository.delete(attempt)
        StudentRepository.commit()

    @staticmethod
    def list_my_attempts(
        student_id: int, quiz_id: Optional[int] = None
    ) -> List[dict]:
        attempts = QuizAttemptRepository.list_for_student(student_id, quiz_id)
        result = []
        for a in attempts:
            d = a.to_summary_dict()
            if a.quiz:
                d['quizTitle'] = a.quiz.title
                d['quizChapterId'] = a.quiz.chapter_id
                d['quizFormLevel'] = a.quiz.form_level
            result.append(d)
        return result

    # ==================================================================
    # Internals
    # ==================================================================

    @staticmethod
    def _check_chapter_unlocked(student_id: int, quiz: Quiz) -> None:
        """Raise ForbiddenError if the student hasn't completed all topics in the chapter."""
        progress = LearningProgressRepository.get_by_student_id(student_id)
        if not progress:
            raise ForbiddenError('Complete all topics in this chapter before taking the quiz.')
        total = TopicRepository.count_by_chapter(quiz.form_level, quiz.chapter_id)
        if total == 0:
            raise ForbiddenError('Complete all topics in this chapter before taking the quiz.')
        completed = LearningProgressRepository.count_completed_in_chapter(
            progress.progress_id, quiz.form_level, quiz.chapter_id
        )
        if completed < total:
            raise ForbiddenError('Complete all topics in this chapter before taking the quiz.')

    @staticmethod
    def _fetch_owned_attempt(student_id: int, attempt_id: int) -> QuizAttempt:
        attempt = QuizAttemptRepository.get(attempt_id)
        if not attempt:
            raise NotFoundError(f'Attempt {attempt_id} not found.')
        if attempt.student_id != student_id:
            raise ForbiddenError('This attempt belongs to another student.')
        return attempt

    @staticmethod
    def _attempt_to_dict(
        attempt: QuizAttempt,
        include_questions: bool = False,
        include_review: bool = False,
    ) -> dict:
        d = attempt.to_summary_dict()
        quiz = attempt.quiz
        d['quiz'] = quiz.to_summary_dict() if quiz else None

        if include_questions and quiz:
            answers = {a.attempt_question_id: a for a in attempt.answers}
            questions = []
            for q in attempt.attempt_questions:
                base = q.to_review_dict() if include_review else q.to_student_dict()
                base['difficulty'] = classify_difficulty(q.stem or '')
                ans = answers.get(q.attempt_question_id)
                base['selectedIndex'] = ans.selected_index if ans else None
                base['isCorrect'] = ans.is_correct if (ans and include_review) else None
                questions.append(base)
            d['questions'] = questions

        return d