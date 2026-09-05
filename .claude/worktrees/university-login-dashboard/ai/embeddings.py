from functools import lru_cache
import numpy as np
from config import Config

@lru_cache(maxsize=1)
def get_model():
    if not Config.AI_ENABLED:
        return None
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(Config.BGE_MODEL)

def generate_embedding(text):
    model = get_model()
    if model is None:
        return None
    vector = model.encode(text, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32).tolist()

def cosine(a, b):
    if not a or not b:
        return 0.0
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0
