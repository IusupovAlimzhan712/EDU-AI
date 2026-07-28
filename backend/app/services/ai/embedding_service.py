"""
OpenAI embedding utilities for hybrid retrieval.

Uses text-embedding-3-small (1536 dims). Vectors are stored as raw float32
bytes (6144 bytes/chunk) in MySQL BLOB columns.
"""
import logging
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIM = 1536
_BATCH_SIZE = 96  # Stay well within OpenAI's 2048-input limit


def _client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def embed_texts(texts: list[str], api_key: str) -> list[np.ndarray]:
    """Embed a list of strings, returning one float32 array per text.

    Batches requests to stay within API limits.
    """
    if not texts:
        return []

    results: list[np.ndarray] = []
    client = _client(api_key)

    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start: start + _BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # API returns items in the same order as input
        for item in sorted(response.data, key=lambda d: d.index):
            results.append(np.array(item.embedding, dtype=np.float32))

    return results


def embed_text(text: str, api_key: str) -> np.ndarray:
    """Embed a single string."""
    return embed_texts([text], api_key)[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity in [-1, 1]; 0.0 on zero-norm vectors."""
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0.0:
        return 0.0
    return float(np.dot(a, b) / norm)


def serialize_embedding(vec: np.ndarray) -> bytes:
    """Serialize float32 array to raw bytes for MySQL BLOB storage."""
    return vec.astype(np.float32).tobytes()


def deserialize_embedding(blob: bytes) -> np.ndarray:
    """Deserialize raw bytes back to a float32 numpy array."""
    return np.frombuffer(blob, dtype=np.float32)
