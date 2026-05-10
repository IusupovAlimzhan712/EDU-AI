"""
Progress & bookmarks routes (current student).

  GET /api/me/progress    -> overall learning progress summary
  GET /api/me/bookmarks   -> list of bookmarked topics
"""
from flask import Blueprint, jsonify

from ..services import TopicService
from ._decorators import auth_required, current_student_id

progress_bp = Blueprint('progress', __name__)


@progress_bp.get('/progress')
@auth_required
def get_progress():
    data = TopicService.get_progress_overview(current_student_id())
    return jsonify(data), 200


@progress_bp.get('/bookmarks')
@auth_required
def get_bookmarks():
    items = TopicService.list_bookmarks(current_student_id())
    return jsonify(items), 200
