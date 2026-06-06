"""
Essay routes — SPM Sejarah Kertas 2 writing practice.

  GET    /api/essay-questions                    list questions with student context
  GET    /api/essay-questions/<id>               get one question (full, with scheme)
  POST   /api/essay-questions/<id>/attempts      start or resume a draft attempt
  GET    /api/me/essay-attempts                  list my attempts
  GET    /api/me/essay-attempts/<id>             get attempt + feedback
  PATCH  /api/me/essay-attempts/<id>/draft       save draft response text
  POST   /api/me/essay-attempts/<id>/submit      submit → triggers grading
  GET    /api/me/essay-attempts/<id>/stream      SSE grading stream
"""
import json
from flask import Blueprint, request, jsonify, Response, stream_with_context

from ..services import EssayService
from ..utils.errors import BadRequestError
from ._decorators import auth_required, current_student_id
from ._utils import _body, _int_arg

essay_bp = Blueprint('essay', __name__)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

@essay_bp.get('/essay-questions')
@auth_required
def list_essay_questions():
    form_level = _int_arg('form_level')
    chapter_id = _int_arg('chapter_id')
    items = EssayService.list_questions(current_student_id(), form_level, chapter_id)
    return jsonify(items), 200


@essay_bp.get('/essay-questions/<int:question_id>')
@auth_required
def get_essay_question(question_id):
    q = EssayService.get_question(question_id)
    return jsonify(q.to_dict()), 200


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------

@essay_bp.post('/essay-questions/<int:question_id>/attempts')
@auth_required
def start_attempt(question_id):
    result = EssayService.start_attempt(current_student_id(), question_id)
    return jsonify(result), 201


@essay_bp.get('/me/essay-attempts')
@auth_required
def list_my_attempts():
    question_id = _int_arg('question_id')
    items = EssayService.list_my_attempts(current_student_id(), question_id)
    return jsonify(items), 200


@essay_bp.get('/me/essay-attempts/<int:attempt_id>')
@auth_required
def get_attempt(attempt_id):
    result = EssayService.get_attempt(current_student_id(), attempt_id)
    return jsonify(result), 200


@essay_bp.patch('/me/essay-attempts/<int:attempt_id>/draft')
@auth_required
def save_draft(attempt_id):
    data = _body()
    response_text = data.get('responseText', '')
    if not isinstance(response_text, str):
        raise BadRequestError('responseText must be a string.')
    result = EssayService.save_draft(current_student_id(), attempt_id, response_text)
    return jsonify(result), 200


@essay_bp.post('/me/essay-attempts/<int:attempt_id>/submit')
@auth_required
def submit_attempt(attempt_id):
    result = EssayService.submit_attempt(current_student_id(), attempt_id)
    return jsonify(result), 200


@essay_bp.post('/me/essay-attempts/<int:attempt_id>/retry')
@auth_required
def retry_grading(attempt_id):
    result = EssayService.retry_grading(current_student_id(), attempt_id)
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# SSE grading stream
# ---------------------------------------------------------------------------

@essay_bp.get('/me/essay-attempts/<int:attempt_id>/stream')
@auth_required
def stream_grading(attempt_id):
    student_id = current_student_id()

    @stream_with_context
    def event_stream():
        try:
            for chunk in EssayService.stream_grading(student_id, attempt_id):
                event_type = chunk.pop('event', 'message')
                payload = json.dumps(chunk, default=str)
                yield f'event: {event_type}\ndata: {payload}\n\n'
        except Exception as exc:
            yield f'event: error\ndata: {json.dumps({"message": str(exc)})}\n\n'

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
