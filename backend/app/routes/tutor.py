"""
AI Tutor routes — SSE streaming chat.

  GET    /api/me/topics/<topic_id>/conversation    load full conversation
  POST   /api/me/topics/<topic_id>/messages        send message (SSE response)
  DELETE /api/me/topics/<topic_id>/conversation    clear conversation
"""
import json
from flask import Blueprint, request, jsonify, Response, stream_with_context

from ..services import TutorService
from ..utils.errors import BadRequestError
from ._decorators import auth_required, current_student_id


tutor_bp = Blueprint('tutor', __name__)


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequestError('Request body must be JSON.')
    return data


@tutor_bp.get('/me/topics/<int:topic_id>/conversation')
@auth_required
def get_conversation(topic_id):
    data = TutorService.get_conversation(current_student_id(), topic_id)
    return jsonify(data), 200


@tutor_bp.delete('/me/topics/<int:topic_id>/conversation')
@auth_required
def clear_conversation(topic_id):
    data = TutorService.clear_conversation(current_student_id(), topic_id)
    return jsonify(data), 200


@tutor_bp.post('/me/tutor/messages')
@auth_required
def send_general_message():
    """POST { question: str, history: [{role, content}]? }  →  SSE stream.

    Searches across ALL babs to find the most relevant pages, then streams
    the AI reply. No server-side conversation is persisted.
    """
    data = _body()
    question = data.get('question')
    history = data.get('history', [])

    if not isinstance(question, str) or not question.strip():
        raise BadRequestError('Field `question` is required.')

    student_id = current_student_id()

    @stream_with_context
    def event_stream():
        try:
            for chunk in TutorService.stream_general_reply(
                student_id=student_id,
                question=question,
                history=history,
            ):
                event_type = chunk.pop('event', 'message')
                payload = json.dumps(chunk)
                yield f'event: {event_type}\ndata: {payload}\n\n'
        except Exception as exc:
            yield f'event: error\ndata: {json.dumps({"message": str(exc)})}\n\n'

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@tutor_bp.post('/me/topics/<int:topic_id>/messages')
@auth_required
def send_message(topic_id):
    """POST with JSON body: { question: string, currentPage: int }.

    Response is SSE — caller must read it as text/event-stream.
    """
    data = _body()
    question = data.get('question')
    current_page = data.get('currentPage')

    if not isinstance(question, str) or not question.strip():
        raise BadRequestError('Field `question` is required.')
    if not isinstance(current_page, int) or current_page < 1:
        raise BadRequestError('Field `currentPage` must be a positive integer.')

    student_id = current_student_id()

    @stream_with_context
    def event_stream():
        try:
            for chunk in TutorService.stream_reply(
                student_id=student_id,
                topic_id=topic_id,
                question=question,
                current_page=current_page,
            ):
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
            'X-Accel-Buffering': 'no',
        },
    )