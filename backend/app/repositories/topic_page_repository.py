"""TopicPageRepository — data access for per-page topic text."""
import re
from typing import List, Optional

from ..extensions import db
from ..models import TopicPage

# Headings: all-uppercase line OR numbered/lettered heading (e.g. "1.2 Tajuk")
_HEADING_RE = re.compile(r'^(?:[A-Z][A-Z\s]{4,}|[\d]+[\.\)]\s+\S)', re.MULTILINE)


def _split_paragraphs(
    text: str,
    topic_id: int,
    topic_name: str,
    page_number: int,
    min_words: int = 25,
) -> list:
    """Split a page's text into paragraph chunks, merging stubs < min_words.

    Returns list of dicts: {topic_id, topic_name, page_number, text_content}.
    Paragraphs inherit the source page_number so the service can still display
    'Rujukan: Hlm X–Y'.
    """
    # Split on blank lines or heading boundaries
    raw = re.split(r'\n{2,}', text.strip())
    chunks = []
    buf = []

    for block in raw:
        block = block.strip()
        if not block:
            continue
        buf.append(block)
        combined = ' '.join(buf)
        if len(combined.split()) >= min_words:
            chunks.append(combined)
            buf = []

    if buf:
        combined = ' '.join(buf)
        if chunks:
            chunks[-1] = chunks[-1] + ' ' + combined
        else:
            chunks.append(combined)

    return [
        {'topic_id': topic_id, 'topic_name': topic_name,
         'page_number': page_number, 'text_content': chunk}
        for chunk in chunks
        if chunk.strip()
    ]


class TopicPageRepository:

    @staticmethod
    def get(topic_id: int, page_number: int) -> Optional[TopicPage]:
        return db.session.query(TopicPage).filter_by(
            topic_id=topic_id, page_number=page_number
        ).first()

    @staticmethod
    def list_for_topic(topic_id: int) -> List[TopicPage]:
        return db.session.query(TopicPage).filter_by(
            topic_id=topic_id
        ).order_by(TopicPage.page_number).all()

    @staticmethod
    def list_for_chapter(form_level: int, chapter_id: int) -> List[TopicPage]:
        """Used by Phase 3 quiz generation — all pages across a chapter."""
        from ..models import Topic
        return (
            db.session.query(TopicPage)
            .join(Topic, TopicPage.topic_id == Topic.topic_id)
            .filter(Topic.form_level == form_level, Topic.chapter_id == chapter_id)
            .order_by(Topic.topic_id, TopicPage.page_number)
            .all()
        )

    @staticmethod
    def delete_all_for_topic(topic_id: int) -> int:
        """Used by the ingest script when re-importing a topic."""
        count = db.session.query(TopicPage).filter_by(topic_id=topic_id).delete()
        db.session.flush()
        return count

    @staticmethod
    def bulk_insert(rows: list) -> None:
        """rows = list of dicts: {topic_id, page_number, text_content, word_count}"""
        if not rows:
            return
        objs = [TopicPage(**r) for r in rows]
        db.session.bulk_save_objects(objs)
        db.session.flush()

    @staticmethod
    def search_relevant(
        topic_ids: List[int],
        query: str,
        limit: int = 8,
    ) -> List[dict]:
        """Keyword-score pages and return the top `limit` as plain dicts."""
        pages, _ = TopicPageRepository.search_relevant_scored(topic_ids, query, limit)
        return pages

    @staticmethod
    def search_relevant_scored(
        topic_ids: List[int],
        query: str,
        limit: int = 8,
    ) -> tuple[List[dict], int]:
        """Paragraph-level keyword scoring; returns the top `limit` chunks.

        Splits each page into paragraphs (≥ 25 words) before scoring, so the
        returned context is tighter and more focused than full-page retrieval.

        Returns (chunks, top_score) where:
          chunks    — list of {topic_id, topic_name, page_number, text_content}
          top_score — keyword-match count of the highest-scoring chunk (0 if none)

        top_score < 3 signals low retrieval confidence.
        """
        from ..models import Topic as TopicModel

        if not topic_ids or not query.strip():
            return [], 0

        rows = (
            db.session.query(TopicPage, TopicModel.topic_name)
            .join(TopicModel, TopicPage.topic_id == TopicModel.topic_id)
            .filter(TopicPage.topic_id.in_(topic_ids))
            .filter(TopicPage.text_content.isnot(None))
            .filter(TopicPage.text_content != '')
            .all()
        )

        # Lazy imports to avoid circular dependency (repositories → services → repositories)
        from ..services.ai.bm25_scorer import BM25Scorer
        from ..services.ai.bm_synonyms import expand_keywords

        # Tokenize + synonym-expand query terms
        raw_keywords = [w.lower() for w in query.split() if len(w) > 2]
        keywords = expand_keywords(raw_keywords)

        # Build paragraph chunks for all pages
        all_chunks: List[dict] = []
        all_token_lists: List[List[str]] = []
        for page, topic_name in rows:
            for chunk in _split_paragraphs(
                page.text_content, page.topic_id, topic_name, page.page_number
            ):
                tokens = BM25Scorer.tokenize(chunk['text_content'])
                all_chunks.append(chunk)
                all_token_lists.append(tokens)

        if not all_chunks:
            return [], 0

        # BM25 corpus stats (computed once across all chunks)
        avg_len, df, n_docs = BM25Scorer.build_corpus_stats(all_token_lists)

        scored = []
        for chunk, tokens in zip(all_chunks, all_token_lists):
            s = BM25Scorer.score(keywords, tokens, avg_len, df, n_docs)
            scored.append((s, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        positive = [(s, c) for s, c in scored if s > 0]
        chosen = positive[:limit] if positive else scored[:limit]
        top_score = int(scored[0][0]) if scored else 0

        return ([c for _, c in chosen], top_score)