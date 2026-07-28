"""
TutorService = Control class for AI Tutor (matches FYP1 Section 4.4
KnowledgeAgent + RoutingAgent responsibilities).

Wires repositories + AI generator. Routes call this; the AI implementation
is injected via the IChatTutor interface.
"""
import logging
import re
from typing import Iterator

from ..extensions import db
from ..repositories import (
    ChatRepository, TopicPageRepository, TopicChunkRepository, StudentRepository,
)
from ..utils.errors import NotFoundError, ValidationError
from .ai import LlmChatTutor, ChatTurn
from .ai.question_classifier import classify_question, is_social_message
from .ai.entity_gate import check_entity_gate, UNCERTAINTY_RESPONSE
from .ai.sentence_extractor import extract_for_mode


logger = logging.getLogger(__name__)

# Minimum top keyword-match score to consider retrieval "confident"
_CONFIDENCE_THRESHOLD = 3

# Semantic similarity floor applied after hybrid retrieval.
# Chunks whose cosine similarity to the query falls below this value are
# dropped from both the LLM context and citation metadata.
# When ALL chunks fail the threshold the original set is kept (safety fallback).
# Has no effect when embeddings are unavailable (_sim is None → BM25-only path).
_SIM_THRESHOLD = 0.50


def _apply_similarity_filter(
    chunks: list,
    threshold: float = _SIM_THRESHOLD,
    prefer_page: int | None = None,
) -> list:
    if not chunks or chunks[0].get('_sim') is None:
        return chunks  # BM25-only: no scores to filter on
    filtered = [c for c in chunks if (c.get('_sim') or 0.0) >= threshold]
    if filtered:
        return filtered
    # All chunks failed threshold — total retrieval failure.
    if prefer_page is not None:
        page_chunks = [c for c in chunks if c.get('page_number') == prefer_page]
        if page_chunks:
            # Current page IS among the retrieved chunks: surface it first so the
            # LLM sees it prominently, then keep the rest as supporting context.
            # (Attribution questions on sparse timeline pages may need neighbouring
            # pages to confirm entity presence.)
            other_chunks = [c for c in chunks if c.get('page_number') != prefer_page]
            return page_chunks + other_chunks
        # Current page NOT in retrieved set at all — the query had zero signal for
        # this page (e.g. "garis masa" where the label is a visual element absent
        # from stored text).  Return empty so _inject_current_page can add ONLY the
        # current page, preventing unrelated pages from polluting the context.
        return []
    return chunks  # last resort for non-page-referential queries


def _strip_internal(chunks: list) -> list:
    """Remove underscore-prefixed internal keys (_sim, etc.) before downstream use."""
    return [{k: v for k, v in c.items() if not k.startswith('_')} for c in chunks]


# Phrases that mean "the page currently being viewed."
# Any of these in a query are a strong signal that the student is asking about
# the specific page open in the reader, not about the chapter in general.
# Covers text-page references ("halaman ini") and visual-element references
# ("peta ini", "gambar ini", "rajah ini", "jadual ini", "graf ini") since
# students on map/diagram/table pages naturally use those terms.
_PAGE_REF_RE = re.compile(
    r'\b(?:halaman\s+ini|muka\s+surat\s+ini|page\s+ini|this\s+page'
    r'|peta\s+ini|gambar\s+ini|rajah\s+ini|jadual\s+ini|graf\s+ini)\b',
    re.IGNORECASE,
)


def _is_page_referential(question: str) -> bool:
    return bool(_PAGE_REF_RE.search(question))


# Detects binary page-attribution questions: "Adakah X disebut/ada/terdapat/dinyatakan pada halaman ini?"
_PAGE_ATTRIBUTION_RE = re.compile(
    r'\bAdakah\b(.+?)\b(?:disebut|disebutkan|ada|terdapat|wujud|dinyatakan|disebutkan)\b',
    re.IGNORECASE | re.DOTALL,
)


def _page_attribution_subject_present(
    question: str,
    page_context: str,
    current_page: int,
) -> bool:
    """For binary page-attribution questions, check if the named subject is
    actually present in the current-page block of the context.

    Returns True (proceed to LLM) when:
      - the question is not an attribution question, OR
      - the named subject IS found in the [Halaman current_page] block, OR
      - the current-page block cannot be located.

    Returns False (short-circuit to UNCERTAINTY_RESPONSE) when the subject is
    deterministically absent from the current-page block.  This prevents the
    LLM from bleeding named entities from neighbouring pages into a page-level
    'Ya' answer.
    """
    m = _PAGE_ATTRIBUTION_RE.search(question)
    if not m:
        return True  # not an attribution question — proceed normally

    subject = m.group(1).strip()
    subject_words = [w for w in subject.split() if len(w) > 2]
    if not subject_words:
        return True  # can't extract meaningful subject — proceed

    # Collect all text labelled [Halaman current_page] in the context.
    page_label = f'[Halaman {current_page}]'
    lines = page_context.split('\n')
    collecting = False
    page_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == page_label:
            collecting = True
            continue
        if stripped.startswith('[Halaman ') and stripped != page_label:
            collecting = False
            continue
        if collecting:
            page_lines.append(line)

    if not page_lines:
        return True  # no current-page block found — proceed (safe fallback)

    current_page_text = '\n'.join(page_lines).lower()
    # If ANY significant word from the subject is found in the current-page text,
    # consider the subject present — proceed to LLM.
    return any(w.lower() in current_page_text for w in subject_words)


def _inject_current_page(
    relevant: list,
    topic_id: int,
    current_page: int,
    limit: int = 8,
) -> list:
    """Ensure current_page chunks appear in the context for page-referential queries.

    If the current page is already in relevant, returns relevant unchanged.
    Otherwise fetches the page's chunks from the DB, prepends them, and trims
    to limit so the total never exceeds 8.  Gracefully returns relevant unchanged
    if the page has no stored chunks.
    """
    if any(r['page_number'] == current_page for r in relevant):
        return relevant

    page_chunks = TopicChunkRepository.get_by_page(topic_id, current_page)
    if not page_chunks:
        return relevant  # nothing to inject

    # Prepend current-page chunks; trim from the tail to stay within limit
    combined = page_chunks + relevant
    return combined[:limit]


_QUESTION_WORDS = frozenset({
    'apa', 'apakah', 'siapa', 'siapakah', 'bila', 'bilakah',
    'di', 'bagaimana', 'mengapa', 'kenapa', 'berapa', 'huraikan',
    'jelaskan', 'nyatakan', 'senaraikan', 'terangkan', 'bincangkan',
})


def _expand_section_title(question: str) -> str:
    """If input looks like a section heading (short, no verb/question word, no ?),
    rewrite it as an explicit instruction so the LLM knows what to do."""
    words = question.split()
    if len(words) > 4 or '?' in question:
        return question
    has_question_word = any(w.lower() in _QUESTION_WORDS for w in words)
    if not has_question_word:
        return f'Terangkan bahagian "{question}" berdasarkan teks rujukan.'
    return question


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

        # Social / casual messages bypass retrieval entirely
        if is_social_message(question):
            tutor = LlmChatTutor()
            for evt in tutor.stream_social_reply(question):
                if evt.get('event') == 'final':
                    evt.setdefault('source_page_start', None)
                    evt.setdefault('source_page_end', None)
                yield evt
            return

        question = _expand_section_title(question)

        from ..models import Topic
        topic = db.session.get(Topic, topic_id)
        if not topic:
            yield {'event': 'error', 'message': 'Topic tidak ditemui.'}
            return

        # ── Retrieval ─────────────────────────────────────────────────
        # Try hybrid (BM25 + semantic) first; fall back to BM25-only page
        # retrieval when no chunks exist, then to the current-page window.
        is_page_ref = _is_page_referential(question)

        relevant, top_score = TopicChunkRepository.search_hybrid(
            topic_ids=[topic_id],
            query=question,
            limit=8,
        )
        if relevant:
            # Pass prefer_page so that when ALL chunks fail the similarity
            # threshold the fallback restricts to the current page instead of
            # returning all retrieved chunks (which may include off-scope pages).
            prefer_page = current_page if is_page_ref else None
            relevant = _strip_internal(
                _apply_similarity_filter(relevant, prefer_page=prefer_page)
            )

        # For page-referential queries guarantee the current page chunk is in
        # context regardless of where hybrid retrieval ranked it — covers the
        # case where the sim filter passed some chunks but missed the current page.
        if is_page_ref:
            relevant = _inject_current_page(relevant, topic_id, current_page)

        if not relevant:
            # Chunks table empty for this topic — fall back to page-level BM25
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

        source_pages = sorted(set(r['page_number'] for r in relevant))
        page_start = source_pages[0]
        page_end   = source_pages[-1]
        page_context = '\n\n'.join(
            f'[Halaman {r["page_number"]}]\n{r["text_content"]}' for r in relevant
        )
        topic_name = topic.topic_name

        # ── Classify question → mode + confidence ─────────────────────
        mode = classify_question(question)
        # Normalize by keyword count: a 2-word query scoring 2 is fully matched,
        # not "low confidence". Only flag low confidence when score is low
        # relative to how many keywords the query actually has.
        query_keywords = [w for w in question.split() if len(w) > 2]
        low_confidence = (
            len(query_keywords) > 2 and top_score < _CONFIDENCE_THRESHOLD
        )
        logger.debug('Question mode=%s low_confidence=%s top_score=%d keywords=%d',
                     mode, low_confidence, top_score, len(query_keywords))

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

        # ── Page attribution gate (page-referential binary questions) ─────
        # For "Adakah X disebut pada halaman ini?" deterministically check the
        # current-page block; block LLM if the named subject is absent, to
        # prevent neighbouring-page entities from bleeding into a page-level 'Ya'.
        if is_page_ref and not _page_attribution_subject_present(
            question, page_context, current_page
        ):
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
        tutor = LlmChatTutor()
        final_payload = None
        try:
            for evt in tutor.stream_reply(
                question=question,
                page_context=page_context,
                chapter_name=topic_name,
                history=history,
                mode=mode,
                low_confidence=low_confidence,
                current_page=current_page,
                page_referential=is_page_ref,
            ):
                if evt.get('event') == 'final':
                    evt['source_page_start'] = page_start
                    evt['source_page_end'] = page_end
                    evt['source_pages'] = source_pages  # precise list, not just min/max
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

        # Social / casual messages bypass retrieval entirely
        if is_social_message(question):
            tutor = LlmChatTutor()
            yield from tutor.stream_social_reply(question)
            return

        question = _expand_section_title(question)

        from ..models import Topic
        all_topic_ids = [t.topic_id for t in db.session.query(Topic.topic_id).all()]

        relevant, top_score = TopicChunkRepository.search_hybrid(
            topic_ids=all_topic_ids,
            query=question,
            limit=10,
        )
        if relevant:
            relevant = _strip_internal(_apply_similarity_filter(relevant))

        if not relevant:
            # Fall back to page-level BM25 if chunks table is empty
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

        # ── Citation metadata ─────────────────────────────────────────
        source_pages = sorted(set(r['page_number'] for r in relevant))
        source_topics = sorted(set(r['topic_name'] for r in relevant))
        page_start = source_pages[0]
        page_end = source_pages[-1]

        page_context = '\n\n'.join(
            f'[{r["topic_name"]}, Halaman {r["page_number"]}]\n{r["text_content"]}'
            for r in relevant
        )

        mode = classify_question(question)
        query_keywords = [w for w in question.split() if len(w) > 2]
        low_confidence = (
            len(query_keywords) > 2 and top_score < _CONFIDENCE_THRESHOLD
        )

        # ── Entity absence gate ───────────────────────────────────────
        if not check_entity_gate(question, page_context):
            yield {
                'event': 'final',
                'content': UNCERTAINTY_RESPONSE,
                'validation_status': 'ok',
                'validation_warning': None,
                'source_page_start': page_start,
                'source_page_end': page_end,
                'source_pages': source_pages,
                'source_topics': source_topics,
            }
            return

        # ── Sentence extraction — tighter context for factual/comparison ──
        page_context = extract_for_mode(page_context, question, mode)

        chat_history = [
            ChatTurn(role=h['role'], content=h['content'])
            for h in (history or [])
            if h.get('role') in ('user', 'assistant') and h.get('content')
        ]

        tutor = LlmChatTutor()
        try:
            for evt in tutor.stream_general_reply(
                question=question,
                page_context=page_context,
                history=chat_history,
                mode=mode,
                low_confidence=low_confidence,
            ):
                if evt.get('event') == 'final':
                    evt['source_page_start'] = page_start
                    evt['source_page_end'] = page_end
                    evt['source_pages'] = source_pages
                    evt['source_topics'] = source_topics
                yield evt
        except Exception as exc:
            logger.exception('General tutor streaming raised')
            yield {'event': 'error', 'message': f'Ralat AI: {exc}'}
