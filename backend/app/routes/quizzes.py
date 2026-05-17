"""
Quiz routes — now with SSE streaming for AI generation.

  GET    /api/quizzes                                  list with progress
  POST   /api/quizzes/<id>/attempts                    start (or resume) attempt
  GET    /api/me/attempts                              list my attempts
  GET    /api/me/attempts/<id>                         resume/view
  GET    /api/me/attempts/<id>/stream                  SSE: AI generates questions
  PATCH  /api/me/attempts/<id>/answers                 save one answer
  POST   /api/me/attempts/<id>/submit                  finalize + grade
"""
import json
from flask import Blueprint, request, jsonify, Response, stream_with_context

from ..services import QuizService
from ..utils.errors import BadRequestError
from ._decorators import auth_required, current_student_id

quizzes_bp = Blueprint('quizzes', __name__)


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequestError('Request body must be JSON.')
    return data


def _int_arg(name):
    raw = request.args.get(name)
    if raw is None or raw == '':
        return None
    try:
        return int(raw)
    except ValueError:
        raise BadRequestError(f'Query parameter `{name}` must be an integer.')


# ---------- Quiz list ----------

@quizzes_bp.get('/quizzes')
@auth_required
def list_quizzes():
    form_level = _int_arg('form_level')
    items = QuizService.list_quizzes_for_student(current_student_id(), form_level)
    return jsonify(items), 200


# ---------- Attempts ----------

@quizzes_bp.post('/quizzes/<int:quiz_id>/attempts')
@auth_required
def start_attempt(quiz_id):
    return jsonify(QuizService.start_attempt(current_student_id(), quiz_id)), 201


@quizzes_bp.get('/me/attempts')
@auth_required
def list_my_attempts():
    quiz_id = _int_arg('quiz_id')
    return jsonify(QuizService.list_my_attempts(current_student_id(), quiz_id)), 200


@quizzes_bp.get('/me/attempts/<int:attempt_id>')
@auth_required
def get_attempt(attempt_id):
    return jsonify(QuizService.get_attempt(current_student_id(), attempt_id)), 200


# ---------- SSE: stream AI question generation ----------

@quizzes_bp.get('/me/attempts/<int:attempt_id>/stream')
@auth_required
def stream_attempt_questions(attempt_id):
    """Server-Sent Events stream of question-generation progress.

    Frontend listens with EventSource. Events:
      - 'question'  : a new question is ready (data: question payload)
      - 'done'      : generation complete (data: {total, target})
      - 'error'     : something went wrong (data: {message})
    """
    student_id = current_student_id()

    @stream_with_context
    def event_stream():
        try:
            for chunk in QuizService.stream_questions(student_id, attempt_id):
                event_type = chunk.pop('event', 'message')
                payload = json.dumps(chunk)
                yield f'event: {event_type}\ndata: {payload}\n\n'
        except Exception as exc:
            yield f'event: error\ndata: {json.dumps({"message": str(exc)})}\n\n'

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # disable nginx buffering if behind proxy
        },
    )


# ---------- Answers + Submit ----------

@quizzes_bp.patch('/me/attempts/<int:attempt_id>/answers')
@auth_required
def save_answer(attempt_id):
    data = _body()
    result = QuizService.save_answer(
        student_id=current_student_id(),
        attempt_id=attempt_id,
        attempt_question_id=data.get('attemptQuestionId'),
        selected_index=data.get('selectedIndex'),
    )
    return jsonify(result), 200


@quizzes_bp.post('/me/attempts/<int:attempt_id>/submit')
@auth_required
def submit_attempt(attempt_id):
    return jsonify(
        QuizService.submit_attempt(current_student_id(), attempt_id)
    ), 200