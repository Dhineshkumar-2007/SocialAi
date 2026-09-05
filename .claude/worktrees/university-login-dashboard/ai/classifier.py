from functools import lru_cache
from config import Config

CATEGORIES = [
    "Water and sanitation",
    "Healthcare",
    "Agriculture",
    "Education",
    "Environment",
    "Infrastructure",
    "Waste management",
    "Energy",
    "Transportation",
    "Employment"
]

@lru_cache(maxsize=1)
def get_classifier():
    if not Config.AI_ENABLED:
        return None
    from transformers import pipeline
    return pipeline(
        "zero-shot-classification",
        model=Config.CLASSIFIER_MODEL
    )

def classify(text):
    clf = get_classifier()
    if clf is None:
        return {"category": "Unclassified", "confidence": 0.0, "scores": {}}
    result = clf(text, CATEGORIES, multi_label=False)
    scores = dict(zip(result["labels"], [float(x) for x in result["scores"]]))
    return {
        "category": result["labels"][0],
        "confidence": float(result["scores"][0]),
        "scores": scores
    }
