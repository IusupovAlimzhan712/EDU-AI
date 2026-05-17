"""
TutorService = Control class for AI Tutor (matches FYP1 Section 4.4
KnowledgeAgent + RoutingAgent responsibilities).

Wires repositories + AI generator. Routes call this; the AI implementation
is injected via the IChatTutor interface.
"""
import logging
from typing import Iterator

from ..extensions import db
from ..repositories import (
    ChatRepository, TopicPageRepository, StudentRepository,
)
from ..utils.errors import NotFoundError, ValidationError
from .ai import OllamaChatTutor, ChatTurn
from .ai.question_classifier import classify_question
from .ai.entity_gate import check_entity_gate, UNCERTAINTY_RESPONSE
from .ai.sentence_extractor import extract_for_mode


logger = logging.getLogger(__name__)

# Minimum top keyword-match score to consider retrieval "confident"
_CONFIDENCE_THRESHOLD = 3


class TutorService:

    # ==================================================================
    # Read
    # ==================================================================

    @staticmethod
    def get_conversation(student_id: int, topic_id: int) -> dict:
        from ..models import Topic
        topic = db.session.get(Topic, topic_id)
        if not topic:
            raise NotFoundError(f'Topic {topic_id} not found.')
        conv = ChatRepository.get_or_create_conversation(student_id, topic_id)
        StudentRepository.commit()
        return conv.to_dict()

    @staticmethod
    def clear_conversation(student_id: int, topic_id: int) -> dict:
        deleted = ChatRepository.delete_conversation(student_id, topic_id)
        if not deleted:
            return {'message': 'No conversation to clear.'}
        StudentRepository.commit()
        return {'message': 'Conversation cleared.'}

    # ==================================================================
    # Stream a reply (per-topic)
    # ==================================================================

    @staticmethod
    def stream_reply(
        student_id: int,
        topic_id: int,
        question: str,
        current_page: int,
    ) -> Iterator[dict]:
        """Generator that yields SSE events while streaming the AI reply."""
        question = (question or '').strip()
        if not question:
            yield {'event': 'error', 'message': 'Soalan kosong.'}
            return
        if len(question) > 1000:
            yield {'event': 'error', 'message': 'Soalan terlalu panjang.'}
            return

        from ..models import Topic
        topic = db.session.get(Topic, topic_id)
        if not topic:
            yield {'event': 'error', 'message': 'Topic tidak ditemui.'}
            return

        # ── Retrieval ─────────────────────────────────────────────────
        relevant, top_score = TopicPageRepository.search_relevant_scored(
            topic_ids=[topic_id],
            query=question,
            limit=8,
        )

        if not relevant:
            # Graceful fallback: current page ± 1
            fallback = []
            for p in (current_page - 1, current_page, current_page + 1):
                if p >= 1:
                    row = TopicPageRepository.get(topic_id, p)
                    if row and row.text_content:
                        fallback.append({'page_number': p, 'text_content': row.text_content})
            if not fallback:
                yield {'event': 'error', 'message': 'Tiada teks tersedia untuk topik ini.'}
                return
            relevant = fallback
            top_score = 0

        page_start = min(r['page_number'] for r in relevant)
        page_end   = max(r['page_number'] for r in relevant)
        page_context = '\n\n'.join(
            f'[Halaman {r["page_number"]}]\n{r["text_content"]}' for r in relevant
        )
        chapter_name = topic.topic_name

        # ── Classify question → mode + confidence ─────────────────────
        mode = classify_question(question)
        low_confidence = top_score < _CONFIDENCE_THRESHOLD
        logger.debug('Question mode=%s low_confidence=%s top_score=%d', mode, low_confidence, top_score)

        # ── Entity absence gate ───────────────────────────────────────
        if not check_entity_gate(question, page_context):
            # Entity expected by the question is absent from context →
            # return a deterministic uncertainty response without calling LLM.
            yield {
                'event': 'final',
                'content': UNCERTAINTY_RESPONSE,
                'validation_status': 'ok',
                'validation_warning': None,
                'source_page_start': page_start,
                'source_page_end': page_end,
            }
            return

        # ── Sentence extraction — tighter context for factual/comparison ──
        page_context = extract_for_mode(page_context, question, mode)

        # ── Persist user message ──────────────────────────────────────
        conv = ChatRepository.get_or_create_conversation(student_id, topic_id)
        ChatRepository.add_message(
            conversation_id=conv.conversation_id,
            role='user',
            content=question,
            source_page_start=page_start,
            source_page_end=page_end,
        )
        StudentRepository.commit()

        # Build history (drop last user message — prompt builder adds it)
        prior_messages = ChatRepository.list_messages(conv.conversation_id)
        history = [
            ChatTurn(role=m.role, content=m.content)
            for m in prior_messages
            if m.role in ('user', 'assistant')
        ]
        history = history[:-1]

        # ── Stream from AI ────────────────────────────────────────────
        tutor = OllamaChatTutor()
        final_payload = None
        try:
            for evt in tutor.stream_reply(
                question=question,
                page_context=page_context,
                chapter_name=chapter_name,
                history=history,
                mode=mode,
                low_confidence=low_confidence,
            ):
                if evt.get('event') == 'final':
                    # Inject source page info so the frontend can display it
                    evt['source_page_start'] = page_start
                    evt['source_page_end'] = page_end
                    final_payload = evt
                yield evt
        except Exception as exc:
            logger.exception('Tutor streaming raised')
            yield {'event': 'error', 'message': f'Ralat AI: {exc}'}
            return

        # ── Persist assistant reply ───────────────────────────────────
        if final_payload:
            ChatRepository.add_message(
                conversation_id=conv.conversation_id,
                role='assistant',
                content=final_payload['content'],
                source_page_start=page_start,
                source_page_end=page_end,
                validation_status=final_payload.get('validation_status', 'ok'),
                validation_warning=final_payload.get('validation_warning'),
            )
            StudentRepository.commit()

    # ==================================================================
    # General (cross-bab) streaming — standalone AI Tutor
    # ==================================================================

    @staticmethod
    def stream_general_reply(
        student_id: int,
        question: str,
        history: list,
    ) -> Iterator[dict]:
        """Search all babs for relevant pages and stream a reply.

        No conversation is persisted server-side — frontend manages history.
        """
        question = (question or '').strip()
        if not question:
            yield {'event': 'error', 'message': 'Soalan kosong.'}
            return
        if len(question) > 1000:
            yield {'event': 'error', 'message': 'Soalan terlalu panjang.'}
            return

        from ..models import Topic
        all_topic_ids = [t.topic_id for t in db.session.query(Topic.topic_id).all()]

        relevant, top_score = TopicPageRepository.search_relevant_scored(
            topic_ids=all_topic_ids,
            query=question,
            limit=8,
        )

        if not relevant:
            yield {
                'event': 'error',
                'message': 'Tiada kandungan berkaitan dijumpai dalam bahan rujukan.',
            }
            return

        page_context = '\n\n'.join(
            f'[{r["topic_name"]}, Halaman {r["page_number"]}]\n{r["text_content"]}'
            for r in relevant
        )

        mode = classify_question(question)
        low_confidence = top_score < _CONFIDENCE_THRESHOLD

        # ── Entity absence gate ───────────────────────────────────────
        if not check_entity_gate(question, page_context):
            yield {
                'event': 'final',
                'content': UNCERTAINTY_RESPONSE,
                'validation_status': 'ok',
                'validation_warning': None,
            }
            return

        # ── Sentence extraction — tighter context for factual/comparison ──
        page_context = extract_for_mode(page_context, question, mode)

        chat_history = [
            ChatTurn(role=h['role'], content=h['content'])
            for h in (history or [])
            if h.get('role') in ('user', 'assistant') and h.get('content')
        ]

        tutor = OllamaChatTutor()
        try:
            yield from tutor.stream_general_reply(
                question=question,
                page_context=page_context,
                history=chat_history,
                mode=mode,
                low_confidence=low_confidence,
            )
        except Exception as exc:
            logger.exception('General tutor streaming raised')
            yield {'event': 'error', 'message': f'Ralat AI: {exc}'}
