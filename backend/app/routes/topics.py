"""
Topic & Chapter routes.

  GET    /api/chapters                               -> list all chapters
  GET    /api/chapters?form_level=4                  -> chapters for a form
  GET    /api/chapters/<fl>/<ch>/cause-effect        -> cause-effect diagram
  GET    /api/topics                                 -> list topics (with status)
  GET    /api/topics/<id>                            -> topic detail (with status)
  POST   /api/topics/<id>/bookmark                   -> bookmark
  DELETE /api/topics/<id>/bookmark                   -> unbookmark
  POST   /api/topics/<id>/complete                   -> mark complete
  DELETE /api/topics/<id>/complete                   -> unmark complete
  GET    /api/topics/<id>/pdf                        -> stream PDF (Step 2)
  GET    /api/topics/<id>/pages/<n>                  -> page text (Step 2, for Phase 3 AI)
"""
from flask import Blueprint, request, jsonify, send_file

from ..services import TopicService
from ..models import CauseEffectDiagram
from ..extensions import db
from ._decorators import auth_required, current_student_id
from ._utils import _int_arg

topics_bp = Blueprint('topics', __name__)


# ---------- Chapters ----------

@topics_bp.get('/chapters')
@auth_required
def list_chapters():
    form_level = _int_arg('form_level')
    chapters = TopicService.list_chapters(form_level)
    return jsonify([c.to_dict() for c in chapters]), 200


@topics_bp.get('/chapters/<int:form_level>/<int:chapter_id>/cause-effect')
@auth_required
def get_cause_effect(form_level, chapter_id):
    diagram = db.session.query(CauseEffectDiagram).filter_by(
        form_level=form_level, chapter_id=chapter_id
    ).first()
    if not diagram:
        return jsonify({'error': 'Not Found', 'message': 'Diagram not yet generated for this chapter.'}), 404
    return jsonify(diagram.to_dict()), 200


# ---------- Topics ----------

@topics_bp.get('/topics')
@auth_required
def list_topics():
    form_level = _int_arg('form_level')
    chapter_id = _int_arg('chapter_id')
    search = request.args.get('search', '').strip() or None
    items = TopicService.list_topics_with_status(
        student_id=current_student_id(),
        form_level=form_level,
        chapter_id=chapter_id,
        search=search,
    )
    return jsonify(items), 200


@topics_bp.get('/topics/<int:topic_id>')
@auth_required
def get_topic(topic_id):
    data = TopicService.get_topic_with_status(current_student_id(), topic_id)
    return jsonify(data), 200


# ---------- Bookmarks ----------

@topics_bp.post('/topics/<int:topic_id>/bookmark')
@auth_required
def bookmark(topic_id):
    bm = TopicService.bookmark_topic(current_student_id(), topic_id)
    return jsonify({'message': 'Bookmarked.', 'bookmark': bm}), 201


@topics_bp.delete('/topics/<int:topic_id>/bookmark')
@auth_required
def unbookmark(topic_id):
    TopicService.remove_bookmark(current_student_id(), topic_id)
    return jsonify({'message': 'Bookmark removed.'}), 200


# ---------- Completion ----------

@topics_bp.post('/topics/<int:topic_id>/complete')
@auth_required
def mark_complete(topic_id):
    ct = TopicService.mark_completed(current_student_id(), topic_id)
    return jsonify({'message': 'Topic marked complete.', 'completion': ct}), 201


@topics_bp.delete('/topics/<int:topic_id>/complete')
@auth_required
def unmark_complete(topic_id):
    TopicService.unmark_completed(current_student_id(), topic_id)
    return jsonify({'message': 'Topic completion removed.'}), 200


# ---------- PDF & per-page text (Step 2) ----------

@topics_bp.get('/topics/<int:topic_id>/pdf')
@auth_required
def get_topic_pdf(topic_id):
    """Stream the topic's PDF file. Auth-protected."""
    abs_path = TopicService.get_pdf_absolute_path(topic_id)
    return send_file(abs_path, mimetype='application/pdf', as_attachment=False)


@topics_bp.get('/topics/<int:topic_id>/pages/<int:page_number>')
@auth_required
def get_topic_page(topic_id, page_number):
    """Return the extracted text for one page. Used by Phase 3 AI tutor."""
    data = TopicService.get_page_text(topic_id, page_number)
    return jsonify(data), 200