from functools import lru_cache
import numpy as np
from config import Config

@lru_cache(maxsize=1)
def get_model():
    if not Config.AI_ENABLED:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(Config.BGE_MODEL, token=Config.HF_TOKEN)
    except Exception:
        return None

# Small text-level cache to avoid re-encoding identical strings (e.g. same
# problem title scanned multiple times within one pipeline run).
_EMBED_CACHE = {}
_EMBED_CACHE_MAX = 4096


def _empty_embedding():
    """Return a stable placeholder for 'no embedding available'."""
    return None


def generate_embedding(text, use_cache=True):
    """Generate a normalized embedding for text, tolerating model absence/failure.

    Returns None if the model is disabled, unavailable, or encoding fails, so
    callers can degrade gracefully to keyword-based logic instead of crashing.
    """
    if not text:
        return None

    if use_cache:
        try:
            key = hash(text)
        except Exception:
            key = None
        if key is not None and key in _EMBED_CACHE:
            return _EMBED_CACHE[key]

    model = get_model()
    vector = None
    if model is not None:
        try:
            encoded = model.encode(text, normalize_embeddings=True)
            vector = np.asarray(encoded, dtype=np.float32).tolist()
        except Exception:
            vector = None

    if use_cache and key is not None and vector is not None:
        if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
            _EMBED_CACHE.clear()
        _EMBED_CACHE[key] = vector
    return vector


def cosine(a, b):
    """Cosine similarity between two vectors, safe against None / empty / bad shapes."""
    if not a or not b:
        return 0.0
    try:
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        if a.ndim != 1 or b.ndim != 1 or a.shape[0] != b.shape[0]:
            return 0.0
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0.0:
            return 0.0
        return float(np.dot(a, b) / denom)
    except (ValueError, TypeError, ArithmeticError, np.linalg.LinAlgError):
        return 0.0
