"""TopicChunkRepository — data access for paragraph-level chunks with embeddings."""
import logging
from collections import defaultdict
from typing import List, Optional, Tuple

from ..extensions import db
from ..models import TopicChunk

logger = logging.getLogger(__name__)


class TopicChunkRepository:

    @staticmethod
    def delete_all_for_topic(topic_id: int) -> int:
        count = db.session.query(TopicChunk).filter_by(topic_id=topic_id).delete()
        db.session.flush()
        return count

    @staticmethod
    def bulk_insert(rows: list) -> None:
        """rows = list of dicts matching TopicChunk column names (snake_case)."""
        if not rows:
            return
        db.session.bulk_save_objects([TopicChunk(**r) for r in rows])
        db.session.flush()

    @staticmethod
    def get_by_page(topic_id: int, page_number: int) -> List[dict]:
        """Return all chunks for a specific topic + page as plain dicts (no internal keys)."""
        from ..models import Topic as TopicModel
        rows = (
            db.session.query(TopicChunk, TopicModel.topic_name)
            .join(TopicModel, TopicChunk.topic_id == TopicModel.topic_id)
            .filter(TopicChunk.topic_id == topic_id)
            .filter(TopicChunk.page_number == page_number)
            .order_by(TopicChunk.chunk_index)
            .all()
        )
        return [
            {
                'topic_id':    chunk.topic_id,
                'topic_name':  topic_name,
                'page_number': chunk.page_number,
                'text_content': chunk.text_content,
            }
            for chunk, topic_name in rows
        ]

    @staticmethod
    def count_embedded(topic_id: int) -> int:
        return (
            db.session.query(TopicChunk)
            .filter_by(topic_id=topic_id)
            .filter(TopicChunk.embedding.isnot(None))
            .count()
        )

    @staticmethod
    def search_hybrid(
        topic_ids: List[int],
        query: str,
        limit: int = 8,
    ) -> Tuple[List[dict], int]:
        """Hybrid BM25 + OpenAI semantic retrieval fused with Reciprocal Rank Fusion.

        Falls back to BM25-only when no chunk has an embedding (e.g. not yet
        embedded after a fresh ingest).

        Returns (chunks, top_bm25_score):
          chunks         — list of {topic_id, topic_name, page_number, text_content}
          top_bm25_score — BM25 score of the highest-ranked chunk (confidence proxy)
        """
        from ..models import Topic as TopicModel
        from ..services.ai.bm25_scorer import BM25Scorer
        from ..services.ai.bm_synonyms import expand_keywords

        if not topic_ids or not query.strip():
            return [], 0

        rows = (
            db.session.query(TopicChunk, TopicModel.topic_name)
            .join(TopicModel, TopicChunk.topic_id == TopicModel.topic_id)
            .filter(TopicChunk.topic_id.in_(topic_ids))
            .filter(TopicChunk.text_content.isnot(None))
            .filter(TopicChunk.text_content != '')
            .all()
        )

        if not rows:
            return [], 0

        # Build chunk dicts (keep _id/_embedding as internal fields for RRF)
        chunks: List[dict] = []
        for chunk, topic_name in rows:
            chunks.append({
                '_id':        chunk.chunk_id,
                '_embedding': chunk.embedding,
                'topic_id':   chunk.topic_id,
                'topic_name': topic_name,
                'page_number': chunk.page_number,
                'text_content': chunk.text_content,
            })

        # ── BM25 ranking ──────────────────────────────────────────────
        raw_keywords = [w.lower() for w in query.split() if len(w) > 2]
        keywords = expand_keywords(raw_keywords)
        token_lists = [BM25Scorer.tokenize(c['text_content']) for c in chunks]
        avg_len, df, n_docs = BM25Scorer.build_corpus_stats(token_lists)

        bm25_scored: List[Tuple[float, dict]] = []
        for c, tokens in zip(chunks, token_lists):
            s = BM25Scorer.score(keywords, tokens, avg_len, df, n_docs)
            bm25_scored.append((s, c))
        bm25_scored.sort(key=lambda x: x[0], reverse=True)
        top_bm25_score = int(bm25_scored[0][0]) if bm25_scored else 0

        # ── Semantic ranking ──────────────────────────────────────────
        sem_scored: Optional[List[Tuple[float, dict]]] = None
        embedded = [c for c in chunks if c['_embedding']]

        if embedded:
            try:
                from ..services.ai.embedding_service import (
                    embed_text, deserialize_embedding, cosine_similarity,
                )
                from ..services.ai.llm_config import get_openai_api_key

                query_vec = embed_text(query, get_openai_api_key())

                sem_scored = []
                for c in chunks:
                    if c['_embedding']:
                        vec = deserialize_embedding(c['_embedding'])
                        sim = cosine_similarity(query_vec, vec)
                    else:
                        sim = 0.0
                    sem_scored.append((sim, c))
                sem_scored.sort(key=lambda x: x[0], reverse=True)

            except Exception as exc:
                logger.warning('Semantic retrieval failed, using BM25-only: %s', exc)
                sem_scored = None

        # ── Reciprocal Rank Fusion ─────────────────────────────────────
        if sem_scored:
            k = 60
            rrf: dict[int, float] = defaultdict(float)
            for rank, (_, c) in enumerate(bm25_scored):
                rrf[c['_id']] += 1.0 / (k + rank + 1)
            for rank, (_, c) in enumerate(sem_scored):
                rrf[c['_id']] += 1.0 / (k + rank + 1)

            chunk_by_id = {c['_id']: c for c in chunks}
            merged = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
            final = [chunk_by_id[cid] for cid, _ in merged[:limit]]
        else:
            positive = [(s, c) for s, c in bm25_scored if s > 0]
            chosen = positive[:limit] if positive else bm25_scored[:limit]
            final = [c for _, c in chosen]

        # Build a sim-score lookup so callers can apply a similarity floor.
        # None signals "no semantic scores available" (BM25-only path).
        sim_by_id: dict = (
            {c['_id']: score for score, c in sem_scored}
            if sem_scored else {}
        )

        result = [
            {
                'topic_id':    c['topic_id'],
                'topic_name':  c['topic_name'],
                'page_number': c['page_number'],
                'text_content': c['text_content'],
                '_sim':        sim_by_id.get(c['_id']),  # None → BM25-only
            }
            for c in final
        ]
        return result, top_bm25_score
