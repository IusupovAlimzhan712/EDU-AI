"""
Lightweight BM25 scorer — no external dependencies.

Used by TopicPageRepository to rank paragraph chunks by relevance to a
BM student query. Standard BM25 (Okapi) parameters k1=1.5, b=0.75.

Usage
-----
from app.services.ai.bm25_scorer import BM25Scorer

# One-shot corpus build (call once per request, not once per item)
avg_len, df, n_docs = BM25Scorer.build_corpus_stats(all_doc_token_lists)

# Score each document
for tokens in all_docs:
    s = BM25Scorer.score(query_tokens, tokens, avg_len, df, n_docs)
"""
import math
from collections import Counter
from typing import Dict, List, Tuple


class BM25Scorer:
    K1 = 1.5
    B  = 0.75

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Lowercase, split, keep tokens ≥ 3 chars."""
        return [w for w in text.lower().split() if len(w) >= 3]

    @staticmethod
    def build_corpus_stats(
        docs: List[List[str]],
    ) -> Tuple[float, Dict[str, int], int]:
        """Pre-compute corpus-level statistics for BM25.

        Args:
            docs: list of already-tokenized documents.

        Returns:
            (avg_doc_len, df_dict, corpus_size)
            avg_doc_len — mean token count across all docs
            df_dict     — document frequency per term
            corpus_size — total number of documents
        """
        n = len(docs)
        if n == 0:
            return 0.0, {}, 0

        total_len = sum(len(d) for d in docs)
        avg_len = total_len / n

        df: Dict[str, int] = {}
        for doc in docs:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1

        return avg_len, df, n

    @staticmethod
    def score(
        query_terms: List[str],
        doc_tokens: List[str],
        avg_doc_len: float,
        df: Dict[str, int],
        n_docs: int,
    ) -> float:
        """Return the BM25 score of one document for the given query terms."""
        if not query_terms or not doc_tokens or n_docs == 0:
            return 0.0

        tf = Counter(doc_tokens)
        dl = len(doc_tokens)
        k1, b = BM25Scorer.K1, BM25Scorer.B

        result = 0.0
        for term in query_terms:
            doc_freq = df.get(term, 0)
            if doc_freq == 0:
                continue
            idf = math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1)
            term_freq = tf.get(term, 0)
            numerator = term_freq * (k1 + 1)
            denominator = term_freq + k1 * (1 - b + b * dl / avg_doc_len)
            result += idf * (numerator / denominator)

        return result
