"""
Sentence extractor for tighter factual-mode context.

For factual questions, feeding the LLM the full retrieved context (potentially
thousands of words) introduces noise that raises hallucination risk. Instead
we extract the N most query-relevant sentences, giving the LLM a concise
target to quote from.

Mode-specific budgets:
  factual    — 5 sentences  (tight extraction, minimise hallucination)
  comparison — 8 sentences  (need more context to compare two things)
  kbat       — None         (full context; analytical questions need breadth)
"""
import re
from typing import Optional

_SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-ZÀ-ɏ一-鿿])')

MODE_SENTENCE_BUDGET: dict = {
    'factual': 5,
    'comparison': 8,
    'kbat': None,
}


def extract_relevant_sentences(
    context: str,
    question: str,
    max_sentences: Optional[int] = 5,
) -> str:
    """Return the most query-relevant sentences from context (at most max_sentences).

    If max_sentences is None, return the full context unchanged.
    Falls back to full context when too little text is available.
    """
    if max_sentences is None or not context.strip():
        return context

    sentences = _split_sentences(context)
    if len(sentences) <= max_sentences:
        return context

    keywords = {w.lower() for w in question.split() if len(w) > 2}
    if not keywords:
        return context

    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for kw in keywords if kw in sent_lower)
        scored.append((score, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_sentences]]

    # Restore sentence order (index in original list)
    order = {s: i for i, s in enumerate(sentences)}
    top.sort(key=lambda s: order.get(s, 0))

    return ' '.join(top)


def extract_for_mode(context: str, question: str, mode: str) -> str:
    """Apply mode-appropriate sentence budget."""
    budget = MODE_SENTENCE_BUDGET.get(mode)
    return extract_relevant_sentences(context, question, max_sentences=budget)


def _split_sentences(text: str) -> list:
    """Split text into sentences, preserving sentence-final punctuation."""
    parts = _SENT_SPLIT_RE.split(text.strip())
    result = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(part)
    return result
