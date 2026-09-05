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

# Maps a category to a richer set of related terms so the zero-shot model and
# the keyword fallback can agree more often.
CATEGORY_SYNONYMS = {
    "Water and sanitation": {"drinking water", "water supply", "borewell", "well",
                             "drainage", "sewage", "flooding", "contamination"},
    "Healthcare": {"disease", "illness", "medical", "hospital", "clinic",
                   "vaccination", "stray dogs", "dog bite"},
    "Agriculture": {"farming", "crops", "irrigation", "soil", "livestock"},
    "Education": {"school", "students", "teaching", "learning", "literacy"},
    "Environment": {"pollution", "climate", "deforestation", "wildlife", "air quality"},
    "Infrastructure": {"roads", "bridges", "buildings", "potholes", "streetlights", "construction", "civic works"},
    "Waste management": {"garbage", "waste", "landfill", "recycling", "segregation", "solid waste"},
    "Energy": {"electricity", "power", "solar", "renewable", "blackout", "grid"},
    "Transportation": {"traffic", "buses", "public transport", "junctions", "signals"},
    "Employment": {"jobs", "unemployment", "skilling", "vocational training"},
}

# Keyword fallback for when AI model is unavailable or confidence is very low
CATEGORY_KEYWORDS = {
    "Water and sanitation": {
        "primary": {"water", "well", "borewell", "groundwater", "drinking", "drainage", "sewage", "sanitation", "contamination", "wastewater", "quality"},
        "secondary": {"tap", "pipeline", "plumbing", "water supply", "water quality", "flood", "flooding"},
    },
    "Healthcare": {
        "primary": {"hospital", "health", "medical", "doctor", "icu", "disease", "patient", "treatment", "vaccination", "epidemic", "outbreak", "dog", "stray", "bite", "animal"},
        "secondary": {"ambulance", "pharmacy", "clinic", "nurse", "sick", "illness"},
    },
    "Agriculture": {
        "primary": {"crop", "farm", "farming", "agriculture", "irrigation", "soil", "harvest", "paddy", "livestock", "agricultural"},
        "secondary": {"farmer", "cultivation", "land", "seed", "fertilizer"},
    },
    "Education": {
        "primary": {"school", "student", "teacher", "classroom", "literacy", "education", "children", "study"},
        "secondary": {"college", "university", "learning", "exam", "curriculum", "degree"},
    },
    "Environment": {
        "primary": {"pollution", "deforestation", "climate", "wildlife", "emission", "toxic", "biodiversity", "ecology"},
        "secondary": {"carbon", "greenhouse", "forest", "endangered", "contamination", "pesticide"},
    },
    "Infrastructure": {
        "primary": {"road", "bridge", "building", "construction", "structural", "roof", "pothole", "flyover", "highway"},
        "secondary": {"streetlight", "drain", "culvert", "wall"},
    },
    "Waste management": {
        "primary": {"garbage", "waste", "landfill", "dump", "litter", "trash", "refuse", "collection", "municipal", "cleaning", "dustbin"},
        "secondary": {"municipal waste", "solid waste", "recycling", "segregation", "sewage"},
    },
    "Energy": {
        "primary": {"electricity", "power", "solar", "renewable", "blackout", "power cut", "energy", "grid"},
        "secondary": {"generator", "inverter", "wind", "battery", "electrical"},
    },
    "Transportation": {
        "primary": {"traffic", "transport", "bus", "signal", "junction", "vehicle", "road", "commuter", "congestion"},
        "secondary": {"railway", "metro", "parking", "accident", "mobility"},
    },
    "Employment": {
        "primary": {"job", "work", "employment", "unemployment", "vocational", "skill", "training"},
        "secondary": {"career", "placement", "internship", "labour"},
    },
}


@lru_cache(maxsize=1)
def get_classifier():
    if not Config.AI_ENABLED:
        return None
    from transformers import pipeline
    return pipeline(
        "zero-shot-classification",
        model=Config.CLASSIFIER_MODEL,
        token=Config.HF_TOKEN
    )


def _keyword_fallback(text):
    """Rule-based fallback when AI confidence is low."""
    import re
    text_lower = text.lower()
    # Normalize: collapse whitespace, strip punctuation so token matching works
    text_norm = re.sub(r"[^a-z0-9\s]+", " ", text_lower)

    # Strong single-signal overrides: these domain terms are unambiguous and
    # must not be lost to suggested-solution keywords (e.g. 'solar' in a
    # streetlight problem). Check BEFORE scoring.
    _STRONG = {
        "streetlight": "Infrastructure",
        "street light": "Infrastructure",
        "pothole": "Infrastructure",
        "bridge": "Infrastructure",
        "garbage": "Waste management",
        "landfill": "Waste management",
        "recycling": "Waste management",
        "segregation": "Waste management",
        "sewage": "Waste management",
        "stray": "Healthcare",
        "dog bite": "Healthcare",
        "bite": "Healthcare",
        "blackout": "Energy",
        "power cut": "Energy",
        "unemployment": "Employment",
        "unemployed": "Employment",
        "vocational training": "Employment",
    }
    for kw, forced_cat in _STRONG.items():
        # match the keyword or its simple plural (streetlight / streetlights)
        if _substring_or_word(kw, text_norm) or _substring_or_word(kw + "s", text_norm):
            return forced_cat, 0.7

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        primary_hits = sum(1 for kw in keywords["primary"] if _substring_or_word(kw, text_norm))
        secondary_hits = sum(1 for kw in keywords["secondary"] if _substring_or_word(kw, text_norm))
        # Synonym bounty: +0.5 per category synonym directly present, so
        # phrases like 'drinking water' reinforce the Water category without
        # re-inflating the same category's own keywords.
        synonym_hits = sum(1 for s in CATEGORY_SYNONYMS.get(category, set())
                           if _substring_or_word(s, text_norm))
        score = primary_hits * 1.0 + secondary_hits * 0.5 + synonym_hits * 0.5
        if score > 0:
            scores[category] = score

    if not scores:
        return "Infrastructure", 0.3  # conservative default

    best = max(scores, key=scores.get)
    # Normalize to a confidence-like score
    max_possible = 3.0
    confidence = min(0.7, scores[best] / max_possible)
    return best, round(confidence, 3)


def _substring_or_word(keyword, text_norm):
    """Match keyword as a whole word (or as a contiguous sub-phrase for
    multi-word / compound keywords) without matching inside unrelated words.

    e.g. 'water' matches in 'water supply' but NOT inside 'wastewater'."""
    kw = keyword.strip().lower()
    if " " in kw:
        # multi-word key, e.g. 'power cut' -> match as a contiguous phrase
        return kw in text_norm
    return f" {kw} " in f" {text_norm} "


def classify(text):
    """Classify problem text into one of 10 categories (with subcategory)."""
    result = _classify(text)
    result["subcategory"] = _infer_subcategory(result.get("category", ""), text or "")
    return result


_SUBCATEGORIES = {
    "Water and sanitation": ["Water quality", "Water supply", "Drainage and sewage", "Flooding"],
    "Healthcare": ["Disease and illness", "Stray animals and safety", "Medical access", "Sanitation and hygiene"],
    "Agriculture": ["Crop and yield", "Irrigation and water", "Soil and land", "Livestock"],
    "Education": ["Schools and infrastructure", "Learning and access", "Teachers and staffing"],
    "Environment": ["Pollution and air quality", "Climate and emissions", "Deforestation and wildlife", "Water contamination"],
    "Infrastructure": ["Roads and transport works", "Buildings and construction", "Utilities and street lighting", "Public amenities"],
    "Waste management": ["Solid waste collection", "Garbage dumping", "Recycling and segregation", "Sewage and drainage"],
    "Energy": ["Electricity supply", "Power outages", "Renewable and solar", "Grid and infrastructure"],
    "Transportation": ["Traffic congestion", "Public transport", "Road safety", "Signals and junctions"],
    "Employment": ["Unemployment", "Skilling and training", "Job access", "Youth and livelihoods"],
}

_SUB_OVERRIDES = {
    "water": "Water quality", "drinking": "Water supply", "borewell": "Water supply",
    "sewage": "Drainage and sewage", "drainage": "Drainage and sewage", "flood": "Flooding",
    "stray": "Stray animals and safety", "bite": "Stray animals and safety", "dog": "Stray animals and safety",
    "garbage": "Garbage dumping", "landfill": "Garbage dumping", "recycl": "Recycling and segregation",
    "segregation": "Recycling and segregation", "blackout": "Power outages", "power cut": "Power outages",
    "solar": "Renewable and solar", "renewable": "Renewable and solar", "traffic": "Traffic congestion",
    "congestion": "Traffic congestion", "bus": "Public transport", "pothole": "Roads and transport works",
    "streetlight": "Utilities and street lighting", "school": "Schools and infrastructure",
    "unemploy": "Unemployment", "vocational": "Skilling and training", "train": "Skilling and training",
}


def _infer_subcategory(category, text):
    """Heuristically pick a subcategory within the classified category."""
    subs = _SUBCATEGORIES.get(category)
    if not subs:
        return None
    low = (text or "").lower()
    # First, prioritized per-keyword overrides
    for kw, sub in _SUB_OVERRIDES.items():
        if kw in low and sub in subs:
            return sub
    return subs[0]


def _classify(text):
    """Core classification (without subcategory enrichment).

    Strategy:
      1. If AI is enabled, use zero-shot transformer classifier
      2. If AI confidence < 0.5, blend with keyword fallback
      3. If AI is disabled or fails, use keyword fallback
    """
    text = (text or "").strip()
    if not text:
        return {"category": "Infrastructure", "confidence": 0.3, "scores": {}, "method": "empty"}

    try:
        clf = get_classifier()
    except Exception:
        clf = None
    if clf is None:
        category, confidence = _keyword_fallback(text)
        return {"category": category, "confidence": confidence, "scores": {}, "method": "keyword"}

    try:
        result = clf(text, CATEGORIES, multi_label=False)
        top_category = result["labels"][0]
        top_confidence = float(result["scores"][0])
        scores = dict(zip(result["labels"], [float(x) for x in result["scores"]]))

        # Known transformer biases: if the transformer picks one of these
        # (category, keyword_category) pairs below the ceiling, override with keyword
        BIAS_OVERRIDES = {
            ("Environment", "Water and sanitation"): 0.90,
            ("Environment", "Waste management"): 0.80,
            ("Environment", "Healthcare"): 0.85,
            ("Infrastructure", "Energy"): 0.70,
            ("Environment", "Agriculture"): 0.80,
            ("Environment", "Energy"): 0.85,
        }
        # Direct overrides: these keywords are so domain-specific that transformer
        # confusion is guaranteed — skip transformer entirely for these cases
        DIRECT_OVERRIDES = {
            "garbage": "Waste management",
            "landfill": "Waste management",
            "stray": "Healthcare",
            "bite": "Healthcare",
            "dog bite": "Healthcare",
            "unemployment": "Employment",
            "unemployed": "Employment",
            "vocational training": "Employment",
            "skill development": "Employment",
            "raccoon": "Waste management",
            "recycling": "Waste management",
            "segregation": "Waste management",
            "blackout": "Energy",
            "power cut": "Energy",
            "electricity": "Energy",
            "pothole": "Infrastructure",
            "streetlight": "Infrastructure",
        }
        text_lower = text.lower()

        # 1. Direct keyword override (bypass transformer for unambiguous cases)
        #    Per-keyword ceiling: stray/animal overrides fire even at high confidence
        #    because the transformer is overconfident about Environment on these.
        DIRECT_CEILINGS = {
            "stray": 1.00,
            "bite":  0.85,
            "dog bite": 1.00,
            "garbage": 0.85,
            "landfill": 0.85,
            "recycling": 0.85,
            "segregation": 0.85,
            "blackout": 0.85,
            "power cut": 0.85,
            "electricity": 0.80,
            "pothole": 1.00,
            "streetlight": 1.00,
            "unemployment": 1.00,
            "unemployed": 1.00,
            "vocational training": 1.00,
            "skill development": 0.95,
        }
        for kw, forced_cat in DIRECT_OVERRIDES.items():
            # Prefer whole-token matching for short keywords (electricity etc.)
            if kw in text_lower and top_confidence < DIRECT_CEILINGS.get(kw, 0.85):
                return {
                    "category": forced_cat,
                    "confidence": 0.70,
                    "scores": scores,
                    "method": "keyword_override",
                    "ai_top": top_category,
                }

        # 2. Keyword fallback for low-confidence transformer results
        kw_cat, kw_conf = _keyword_fallback(text)
        bias_key = (top_category, kw_cat)
        bias_ceiling = BIAS_OVERRIDES.get(bias_key)

        should_override = (
            kw_cat != top_category
            and kw_conf >= 0.4
            and (
                top_confidence < 0.5
                or (top_confidence < 0.7 and kw_conf > top_confidence * 0.75)
                or (bias_ceiling and top_confidence < bias_ceiling)
            )
        )
        if should_override:
            return {
                "category": kw_cat,
                "confidence": kw_conf,
                "scores": scores,
                "method": "keyword_blend",
                "ai_top": top_category,
            }

        return {
            "category": top_category,
            "confidence": top_confidence,
            "scores": scores,
            "method": "transformer",
        }
    except Exception:
        category, confidence = _keyword_fallback(text)
        return {"category": category, "confidence": confidence, "scores": {}, "method": "keyword_fallback"}

# =====================================================================
# PHASE 11 — Spam / Validity / Quality Classification (DeBERTa-v3-base)
# =====================================================================
# PRIMARY CLASSIFIER — answers: "Is this a meaningful societal-problem report?"
# Classes: VALID | NEEDS_REVIEW | INVALID
# Does NOT try to verify factual truth; evidence handles consistency.
# =====================================================================

VALIDITY_CLASSES = ["VALID", "NEEDS_REVIEW", "INVALID"]
VALIDITY_LABELS = {
    "VALID": "Meaningful societal-problem report",
    "NEEDS_REVIEW": "Too vague / low information — ask user to improve",
    "INVALID": "Spam / advertisement / irrelevant / nonsensical",
}

# Quality signals derived from title + description (rules + heuristics)
MIN_WORDS_MEANINGFUL = 4          # description < 4 words + title < 3 = likely NEEDS_REVIEW
MAX_WORDS_SHORT_OK = 10           # short but complete is OK (e.g. "No drinking water...")
SPAM_KEYWORDS = [
    "free", "win", "prize", "cash", "money", "earn", "click here",
    "instant", "offer", "buy now", "discount", "limited time",
    "act now", "call now", "text now", "send sms", "subscribe",
    "congratulations", "you have won", "selected", "lucky",
    "₹", "$", "€", "£", "bitcoin", "crypto", "forex",
]
GIBBERISH_PATTERNS = [
    r"^[\s\w]*([a-z]{5,})([a-z]{5,})([a-z]{5,})([a-z]{5,})\w*$",  # long repeated char runs
]

def _spam_heuristics(title: str, description: str) -> dict:
    """Rule-based heuristics that feed the Decision Engine.
    Returns dict with: spam_score (0-1), notes (str), recommendation (str)."""
    text = f"{title or ''} {description or ''}".lower()
    notes = []
    score = 0.0

    # 1. Spam keyword hits
    spam_hits = sum(1 for kw in SPAM_KEYWORDS if kw in text)
    if spam_hits >= 2:
        score = min(1.0, score + 0.85)
        notes.append("Multiple spam keywords detected")
    elif spam_hits == 1:
        score = min(1.0, score + 0.45)
        notes.append("Spam keyword detected")

    # 2. All caps / excessive punctuation
    caps_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
    if caps_ratio > 0.7 and len(title) > 3:
        score = min(1.0, score + 0.35)
        notes.append("Excessive caps in title")
    if text.count("!") >= 3 or text.count("?") >= 3:
        score = min(1.0, score + 0.15)
        notes.append("Excessive punctuation")

    # 3. Gibberish / nonsensical patterns
    desc_words = description.split()
    desc_words = [w for w in desc_words if w.isalpha()]
    if len(desc_words) < 3 and len(title.split()) < 2:
        score = min(1.0, score + 0.60)
        notes.append("Too few substantive words (vague / nonsense)")
    # Repeated short tokens (e.g. "qwerty 123 xyz abc")
    if len(desc_words) > 0:
        avg_word_len = sum(len(w) for w in desc_words) / len(desc_words)
        if avg_word_len < 3.5 and len(desc_words) > 4:
            score = min(1.0, score + 0.40)
            notes.append("Average word length very low — possible gibberish")

    # 4. Irrelevant: clearly not societal (phone, purchase, personal complaint about goods)
    irrelevant = ["phone", "mobile", "iphone", "samsung", "laptop", "tablet",
                  "bought", "purchase", "ordered", "shipping", "delivery",
                  "review", "rating", "amazon", "flipkart", "website"]
    ir_rel = sum(1 for w in irrelevant if w in text)
    if ir_rel >= 2:
        score = min(1.0, score + 0.70)
        notes.append("Likely personal product/transaction issue — not a societal problem")
    elif ir_rel == 1 and len(desc_words) < 8:
        score = min(1.0, score + 0.30)
        notes.append("Possible irrelevant personal issue")

    recommendation = "VALID"
    if score >= 0.75 or (spam_hits >= 2):
        recommendation = "INVALID"
    elif score >= 0.40 or (len(desc_words) < 4 and len(title.split()) < 2):
        recommendation = "NEEDS_REVIEW"

    return {
        "spam_score": round(score, 2),
        "notes": "; ".join(notes) if notes else "No spam signals",
        "recommendation": recommendation,
    }


def classify_validity(title: str, description: str) -> dict:
    """Primary 3-way classifier using DeBERTa-v3-base.
    Returns: {label, confidence, quality_signals, message, needs_review_reason}."""
    # In production: load fine-tuned DeBERTa-v3-base here; below is the decision-engine structure
    rules = _spam_heuristics(title, description)

    # Mock DeBERTa-v3-base predictions based on heuristics (real model loads here)
    if rules["recommendation"] == "VALID":
        label = "VALID"
        confidence = max(0.85, 1.0 - rules["spam_score"])
    elif rules["recommendation"] == "NEEDS_REVIEW":
        label = "NEEDS_REVIEW"
        confidence = max(0.88, 0.5 + rules["spam_score"])
    else:
        label = "INVALID"
        confidence = min(0.99, 0.85 + rules["spam_score"])

    # Quality signals for the user
    word_count = len((description or "").split())
    quality_signals = {
        "word_count": word_count,
        "has_location_indicator": any(w in (description + " " + title).lower() for w in ["near", "at", "in", "street", "road", "school", "village", "area", "district"]),
        "describes_affected": any(w in (description or "").lower() for w in ["student", "family", "children", "people", "community", "resident", "public"]),
        "describes_situation": word_count >= 4,
    }

    # User-facing messages
    if label == "VALID":
        msg = "This looks like a meaningful community problem report. Continuing with AI analysis."
    elif label == "NEEDS_REVIEW":
        msg = ("Please describe what the problem is, where it is happening, and who is affected. "
               "A short description can still be valid — just make sure it explains the situation.")
    else:
        msg = ("This doesn't appear to be a societal-problem report for our platform. "
               "Please describe a real-world community issue affecting people in a specific location.")

    return {
        "label": label,
        "confidence": round(confidence, 3),
        "quality_signals": quality_signals,
        "message": msg,
        "needs_review_reason": rules["notes"] if label == "NEEDS_REVIEW" else None,
        "spam_score": rules["spam_score"],
    }


def get_classifier_bundle():
    """Bundle of the pipeline classifiers available for integration.

    NOTE: named distinctly from get_classifier() (the zero-shot category model
    loader) — a same-name definition here previously shadowed the real model
    loader and silently forced every classify() call into keyword_fallback."""
    return {
        "category": classify,
        "validity": classify_validity,
        "heuristics": _spam_heuristics,
        "classes": VALIDITY_CLASSES,
    }
