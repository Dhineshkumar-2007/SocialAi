from functools import lru_cache
import numpy as np
from PIL import Image
from config import Config
from ai.embeddings import generate_embedding


@lru_cache(maxsize=1)
def get_vision():
    if not Config.AI_ENABLED:
        return None
    from transformers import AutoProcessor
    try:
        from transformers import AutoModelForVision2Seq
    except ImportError:
        # transformers >= 4.50 renamed the class
        from transformers import AutoModelForImageTextToText as AutoModelForVision2Seq
    processor = AutoProcessor.from_pretrained(Config.VISION_MODEL, token=Config.HF_TOKEN)
    model = AutoModelForVision2Seq.from_pretrained(Config.VISION_MODEL, token=Config.HF_TOKEN)
    return processor, model


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / norm) if norm else 0.0


def _evidence_decision(similarity):
    """Convert semantic similarity into structured evidence decision.

    Thresholds tuned for real-world photo evidence:
      < 0.45  -> irrelevant   (photo clearly unrelated to problem)
      0.45-0.62 -> uncertain  (partial relevance, needs human review)
      >= 0.62 -> supporting  (photo aligns with problem description)
    """
    if similarity < 0.45:
        return {"confidence": 0.0, "supports_report": False, "evidence_status": "irrelevant"}
    if similarity < 0.62:
        # Uncertain: image related but not conclusive
        confidence = 0.25 + (similarity - 0.45) * 0.3
        return {"confidence": min(0.45, confidence), "supports_report": False, "evidence_status": "uncertain"}
    # Supporting: image clearly aligns with the problem
    confidence = 0.65 + (similarity - 0.62) * 0.5
    return {"confidence": min(0.95, confidence), "supports_report": True, "evidence_status": "supporting"}


def analyze_image(path, problem_text, title=None, description=None):
    """Analyze an evidence image against a problem report.

    Pipeline:
      1. BLIP caption generation from the image
      2. Semantic similarity between caption and problem text (title + description)
      3. Structured evidence decision based on similarity thresholds
    """
    vision = get_vision()
    if vision is None:
        return {
            "caption": "Vision model disabled",
            "supports_report": False,
            "confidence": 0.0,
            "evidence_status": "disabled",
        }

    processor, model = vision
    try:
        image = Image.open(path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        output = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(output[0], skip_special_tokens=True)

        title_text = title or problem_text
        desc_text = description or problem_text

        title_emb = generate_embedding(title_text)
        desc_emb = generate_embedding(desc_text)
        img_emb = generate_embedding(caption)

        title_sim = cosine_similarity(title_emb, img_emb)
        desc_sim = cosine_similarity(desc_emb, img_emb)
        # Description carries slightly more weight than title alone
        similarity = title_sim * 0.40 + desc_sim * 0.60

        decision = _evidence_decision(similarity)

        return {
            "caption": caption,
            "supports_report": decision["supports_report"],
            "confidence": round(decision["confidence"], 3),
            "similarity": round(float(similarity), 3),
            "title_relevance": round(float(title_sim), 3),
            "description_relevance": round(float(desc_sim), 3),
            "image_relevance": round(float(similarity), 3),
            "evidence_status": decision["evidence_status"],
        }
    except Exception as exc:
        return {
            "caption": f"Unable to analyze image: {str(exc)}",
            "supports_report": False,
            "confidence": 0.0,
            "similarity": 0.0,
            "evidence_status": "error",
        }
    