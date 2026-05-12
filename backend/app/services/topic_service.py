"""
TopicService — implementation of the `TopicManager` Control class
described in Table 4.28 / Section 6.3.2 of the FYP1 report.

Responsibilities:
  - Browse syllabus by Form Level + Chapter (UC 4.3.16)
  - Display topic content (UC 4.3.12)
  - Bookmark / unbookmark a topic (UC 4.3.14)
  - Mark topic completed / uncompleted (UC 4.3.7)
  - Track progress (read-side queries for the /me/progress route)
"""
from typing import List, Optional

from ..models import Topic, Chapter
from ..repositories import (
    ChapterRepository,
    TopicRepository,
    LearningProgressRepository,
    StudentRepository,
)
from ..utils.errors import NotFoundError, ValidationError


class TopicService:

    # =====================================================================
    # Read-side
    # =====================================================================

    @staticmethod
    def list_chapters(form_level: Optional[int] = None) -> List[Chapter]:
        if form_level is not None:
            if form_level not in (4, 5):
                raise ValidationError(errors={'formLevel': 'Form level must be 4 or 5'})
            return ChapterRepository.list_by_form_level(form_level)
        return ChapterRepository.list_all()

    @staticmethod
    def list_topics(
        form_level: Optional[int] = None,
        chapter_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Topic]:
        if form_level is not None and form_level not in (4, 5):
            raise ValidationError(errors={'formLevel': 'Form level must be 4 or 5'})
        if chapter_id is not None and chapter_id < 1:
            raise ValidationError(errors={'chapterId': 'Chapter id must be >= 1'})
        return TopicRepository.list_filtered(
            form_level=form_level,
            chapter_id=chapter_id,
            search=search,
        )

    @staticmethod
    def get_topic(topic_id: int) -> Topic:
        topic = TopicRepository.get_by_id(topic_id)
        if not topic:
            raise NotFoundError(f'Topic {topic_id} not found.')
        return topic

    # =====================================================================
    # Topic + status (for the topics-browser cards that show
    # bookmark/completion state)
    # =====================================================================

    @staticmethod
    def list_topics_with_status(
        student_id: int,
        form_level: Optional[int] = None,
        chapter_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        topics = TopicService.list_topics(
            form_level=form_level, chapter_id=chapter_id, search=search
        )
        progress = LearningProgressRepository.get_by_student_id(student_id)
        if not progress:
            # Should never happen — created on registration — but be safe.
            completed_ids, bookmarked_ids = set(), set()
        else:
            completed_ids = set(
                LearningProgressRepository.list_completed_topic_ids(progress.progress_id)
            )
            bookmarked_ids = set(
                LearningProgressRepository.list_bookmarked_topic_ids(progress.progress_id)
            )

        result = []
        for t in topics:
            d = t.to_summary_dict()
            d['isCompleted'] = t.topic_id in completed_ids
            d['isBookmarked'] = t.topic_id in bookmarked_ids
            result.append(d)
        return result

    @staticmethod
    def get_topic_with_status(student_id: int, topic_id: int) -> dict:
        topic = TopicService.get_topic(topic_id)
        progress = LearningProgressRepository.get_by_student_id(student_id)
        completed = bookmarked = False
        if progress:
            completed = LearningProgressRepository.get_completed_topic(
                progress.progress_id, topic_id
            ) is not None
            bookmarked = LearningProgressRepository.get_bookmark(
                progress.progress_id, topic_id
            ) is not None
        d = topic.to_dict()
        d['isCompleted'] = completed
        d['isBookmarked'] = bookmarked
        return d

    # =====================================================================
    # Bookmarks
    # =====================================================================

    @staticmethod
    def bookmark_topic(student_id: int, topic_id: int) -> dict:
        progress = TopicService._get_progress_or_raise(student_id)
        # Ensure the topic actually exists
        TopicService.get_topic(topic_id)
        bm = LearningProgressRepository.add_bookmark(progress.progress_id, topic_id)
        StudentRepository.commit()
        return bm.to_dict()

    @staticmethod
    def remove_bookmark(student_id: int, topic_id: int) -> None:
        progress = TopicService._get_progress_or_raise(student_id)
        removed = LearningProgressRepository.remove_bookmark(
            progress.progress_id, topic_id
        )
        if not removed:
            raise NotFoundError('Bookmark not found.')
        StudentRepository.commit()

    @staticmethod
    def list_bookmarks(student_id: int) -> List[dict]:
        progress = TopicService._get_progress_or_raise(student_id)
        bookmarks = LearningProgressRepository.list_bookmarks(progress.progress_id)
        result = []
        for bm in bookmarks:
            entry = bm.topic.to_summary_dict() if bm.topic else {}
            entry['bookmarkedAt'] = (
                bm.bookmarked_at.isoformat() if bm.bookmarked_at else None
            )
            result.append(entry)
        return result

    # =====================================================================
    # Completion
    # =====================================================================

    @staticmethod
    def mark_completed(student_id: int, topic_id: int) -> dict:
        progress = TopicService._get_progress_or_raise(student_id)
        TopicService.get_topic(topic_id)
        ct = LearningProgressRepository.mark_completed(progress.progress_id, topic_id)
        StudentRepository.commit()
        return ct.to_dict()

    @staticmethod
    def unmark_completed(student_id: int, topic_id: int) -> None:
        progress = TopicService._get_progress_or_raise(student_id)
        removed = LearningProgressRepository.unmark_completed(
            progress.progress_id, topic_id
        )
        if not removed:
            raise NotFoundError('Completion record not found.')
        StudentRepository.commit()

    # =====================================================================
    # Progress overview
    # =====================================================================

    @staticmethod
    def get_progress_overview(student_id: int) -> dict:
        progress = TopicService._get_progress_or_raise(student_id)
        completed_ids = LearningProgressRepository.list_completed_topic_ids(
            progress.progress_id
        )
        bookmarked_ids = LearningProgressRepository.list_bookmarked_topic_ids(
            progress.progress_id
        )

        all_topics = TopicRepository.list_filtered()
        total = len(all_topics)
        completion_rate = (len(completed_ids) / total * 100) if total else 0.0

        # Per-chapter completion breakdown
        per_chapter = {}
        for t in all_topics:
            key = f'F{t.form_level}-C{t.chapter_id}'
            if key not in per_chapter:
                per_chapter[key] = {
                    'formLevel': t.form_level,
                    'chapterId': t.chapter_id,
                    'chapterName': t.chapter.chapter_name if t.chapter else '',
                    'totalTopics': 0,
                    'completedTopics': 0,
                }
            per_chapter[key]['totalTopics'] += 1
            if t.topic_id in set(completed_ids):
                per_chapter[key]['completedTopics'] += 1

        return {
            'progressId': progress.progress_id,
            'studentId': student_id,
            'totalTopics': total,
            'completedTopicsCount': len(completed_ids),
            'bookmarkedTopicsCount': len(bookmarked_ids),
            'completionRate': round(completion_rate, 2),
            'lastUpdated': progress.last_updated.isoformat()
                if progress.last_updated else None,
            'byChapter': sorted(
                per_chapter.values(),
                key=lambda x: (x['formLevel'], x['chapterId']),
            ),
        }
    
    # =====================================================================
    # PDF & per-page text (used by viewer + Phase 3 AI)
    # =====================================================================

    @staticmethod
    def get_pdf_absolute_path(topic_id: int) -> str:
        """Resolve a topic's PDF to an absolute path on disk.

        Raises NotFoundError if the topic doesn't exist or has no PDF
        registered, and if the file is missing on disk.
        """
        import os
        from flask import current_app
        topic = TopicService.get_topic(topic_id)
        if not topic.pdf_path:
            raise NotFoundError(f'Topic {topic_id} has no PDF registered.')
        # PDFs live in backend/static/pdfs/<relative path>
        backend_root = os.path.dirname(current_app.root_path)
        abs_path = os.path.join(backend_root, 'static', 'pdfs', topic.pdf_path)
        if not os.path.isfile(abs_path):
            raise NotFoundError(
                f'PDF file is registered but missing on disk: {topic.pdf_path}'
            )
        return abs_path

    @staticmethod
    def get_page_text(topic_id: int, page_number: int) -> dict:
        """Return one page's extracted text + word count."""
        from ..repositories import TopicPageRepository
        # Confirm topic exists (also confirms 404 vs page-not-found)
        TopicService.get_topic(topic_id)
        page = TopicPageRepository.get(topic_id, page_number)
        if not page:
            raise NotFoundError(
                f'Page {page_number} not found for topic {topic_id}. '
                f'Has the PDF been ingested?'
            )
        return page.to_dict()

    # =====================================================================
    # Helpers
    # =====================================================================

    @staticmethod
    def _get_progress_or_raise(student_id: int):
        progress = LearningProgressRepository.get_by_student_id(student_id)
        if not progress:
            raise NotFoundError('Learning progress record missing for this student.')
        return progress
