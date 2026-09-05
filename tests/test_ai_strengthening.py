"""Unit tests for the strengthened AI module.

These tests exercise the pure-logic and graceful-degradation paths WITHOUT
downloading or loading heavyweight transformer models (AI_ENABLED is forced
off here), so the suite runs fast and works offline.
"""
import os

os.environ["AI_ENABLED"] = "false"

import numpy as np
import pytest

from config import Config
from ai import embeddings
from ai.classifier import (
    classify,
    _classify,
    _keyword_fallback,
    _infer_subcategory,
    _substring_or_word,
)
from ai.skills import extract_skills
from ai.priority import calculate_priority
from ai.duplicate import find_duplicates, haversine_km
from ai.matcher import _skill_in_text, _get_adaptive_penalty


# ---------------------------------------------------------------------------
# Robustness / error handling
# ---------------------------------------------------------------------------
def test_generate_embedding_graceful_when_disabled(monkeypatch):
    # AI_ENABLED=false -> get_model() is None -> returns None, no crash
    monkeypatch.setattr(Config, "AI_ENABLED", False)
    from ai.embeddings import get_model
    get_model.cache_clear()
    assert embeddings.generate_embedding("anything") is None
    assert embeddings.generate_embedding(None) is None
    assert embeddings.generate_embedding("") is None
    get_model.cache_clear()


def test_cosine_robust_to_bad_input():
    assert embeddings.cosine(None, None) == 0.0
    assert embeddings.cosine([], [1, 2]) == 0.0
    assert embeddings.cosine([1, 2, 3], [1, 2]) == 0.0  # mismatched shapes
    assert embeddings.cosine([0.0, 0.0], [1.0, 1.0]) == 0.0  # zero norm
    assert embeddings.cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert embeddings.cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_classify_handles_empty_none():
    r = classify("")
    assert r["category"] in {"Infrastructure"}  # conservative default
    assert r["method"] in ("empty",)
    rs = classify(None)
    assert rs["category"]


def test_classifier_returns_valid_category_and_subcategory():
    for text in [
        "Contaminated drinking water in village",
        "Stray dogs biting children near school",
        "Garbage dumped on residential street",
        "Power cuts for 12 hours daily",
        "Potholes on the main road",
    ]:
        r = classify(text)
        assert r["category"] in {
            "Water and sanitation", "Healthcare", "Agriculture", "Education",
            "Environment", "Infrastructure", "Waste management", "Energy",
            "Transportation", "Employment",
        }
        # subcategory should be one of the valid options for that category
        subs = {
            "Water and sanitation": ["Water quality", "Water supply", "Drainage and sewage", "Flooding"],
            "Healthcare": ["Disease and illness", "Stray animals and safety", "Medical access", "Sanitation and hygiene"],
            "Infrastructure": ["Roads and transport works", "Buildings and construction", "Utilities and street lighting", "Public amenities"],
            "Waste management": ["Solid waste collection", "Garbage dumping", "Recycling and segregation", "Sewage and drainage"],
            "Energy": ["Electricity supply", "Power outages", "Renewable and solar", "Grid and infrastructure"],
            "Transportation": ["Traffic congestion", "Public transport", "Road safety", "Signals and junctions"],
            "Employment": ["Unemployment", "Skilling and training", "Job access", "Youth and livelihoods"],
            "Agriculture": ["Crop and yield", "Irrigation and water", "Soil and land", "Livestock"],
            "Education": ["Schools and infrastructure", "Learning and access", "Teachers and staffing"],
            "Environment": ["Pollution and air quality", "Climate and emissions", "Deforestation and wildlife", "Water contamination"],
        }[r["category"]]
        assert r["subcategory"] in subs


# ---------------------------------------------------------------------------
# Classification accuracy (override + subcategory logic)
# ---------------------------------------------------------------------------
def test_direct_override_garbage_is_waste_management():
    r = classify("garbage landfill dumping")
    assert r["category"] == "Waste management"


def test_direct_override_stray_is_healthcare():
    r = classify("stray dog bite")
    assert r["category"] == "Healthcare"


def test_direct_override_energy_keywords():
    assert classify("blackout and power cut")["category"] == "Energy"
    assert classify("electricity supply failing")["category"] == "Energy"


def test_direct_override_infrastructure_keywords():
    assert classify("pothole on the road")["category"] == "Infrastructure"
    assert classify("streetlight not working")["category"] == "Infrastructure"


def test_employment_wins_over_training_subject():
    # A vocational-training problem that mentions 'solar' as the training
    # topic must be classified as Employment (problem domain), not Energy.
    r = classify("500+ unemployed youth need vocational training in solar installation")
    assert r["category"] == "Employment"
    assert r["subcategory"] == "Unemployment"


def test_subcategory_inference():
    assert _infer_subcategory("Water and sanitation", "sewage overflow") == "Drainage and sewage"
    assert _infer_subcategory("Water and sanitation", "borewell drinking") == "Water supply"
    assert _infer_subcategory("Energy", "solar panel") == "Renewable and solar"
    assert _infer_subcategory("Infrastructure", "streetlight") == "Utilities and street lighting"
    assert _infer_subcategory("Unknown category", "anything") is None


def test_substring_or_word_matching():
    # short keyword must not match inside a longer word ('water' != 'wastewater')
    assert _substring_or_word("water", "water supply is contaminated") is True
    assert _substring_or_word("water", "the wastewater n") is False
    # longer/multiword keys still substring match
    assert _substring_or_word("power cut", "there was a power cut") is True


def test_keyword_fallback_returns_valid():
    cat, conf = _keyword_fallback("broken streetlight near the highway")
    assert cat in {"Infrastructure", "Transportation"}
    assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Skills extraction
# ---------------------------------------------------------------------------
def test_skills_word_aware():
    skills = extract_skills("solar energy for power")
    assert "Energy" in skills
    # no spurious software-skill from 'ai' inside unrelated words
    assert "Artificial Intelligence" not in extract_skills("rain flooded the area")


def test_skills_empty():
    assert extract_skills("") == []


# ---------------------------------------------------------------------------
# Priority scoring accuracy + edges
# ---------------------------------------------------------------------------
def test_priority_levels():
    low = calculate_priority({"title": "pothole on road", "description": ""}, evidence_score=0, duplicate_count=0)
    assert low["level"] in {"low", "medium"}
    crit = calculate_priority(
        {"title": "toxic waste poisoning community water causing deaths", "description": "children are getting sick"},
        evidence_score=90, duplicate_count=3,
    )
    assert crit["level"] == "critical"
    assert crit["score"] >= 70


def test_priority_evidence_gap_bonus():
    # Critical-severity problem with NO evidence gets a bonus to reach critical
    r = calculate_priority(
        {"title": "building collapse risk after fire explosion", "description": "emergency"},
        evidence_score=0, duplicate_count=0,
    )
    assert r["level"] in {"critical", "high"}
    assert r["factors"]["evidence_gap_bonus"] >= 0


def test_priority_handles_missing_fields():
    r = calculate_priority({}, evidence_score=0, duplicate_count=0)
    assert 0 <= r["score"] <= 100
    assert "factors" in r


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
def test_haversine_edges():
    assert haversine_km(None, 5, 10, 6) is None
    assert haversine_km(13.0, 80.0, 13.0, 80.0) < 0.001
    far = haversine_km(13.0, 80.0, 14.0, 81.0)
    assert far > 100


def test_duplicate_detection_basic():
    base = {"id": 1, "embedding": [0.1] * 384, "latitude": 13.0, "longitude": 80.2,
            "category": "Water and sanitation"}
    others = [
        {"id": 2, "embedding": [0.1] * 384, "latitude": 13.01, "longitude": 80.21,
         "category": "Water and sanitation"},
        {"id": 3, "embedding": [0.9] * 384, "latitude": 13.5, "longitude": 80.5,
         "category": "Infrastructure"},
    ]
    dups = find_duplicates(base, others)
    assert len(dups) == 1
    assert dups[0]["problem_id"] == 2


def test_duplicate_handles_missing_embedding():
    base = {"id": 1, "embedding": None, "latitude": 13.0, "longitude": 80.2}
    others = [{"id": 2, "embedding": None, "latitude": 13.0, "longitude": 80.2}]
    # no crash; should not flag itself
    assert find_duplicates(base, others) == []


# ---------------------------------------------------------------------------
# Matcher helpers (pure logic, no DB)
# ---------------------------------------------------------------------------
def test_skill_in_text_word_boundary():
    # single-token skill matches only as whole word
    assert _skill_in_text("AI", {"ai", "artificial"}, "artificial ai") is True
    assert _skill_in_text("AI", {"airport"}, "airport") is False
    # multi-word skill matches as substring
    assert _skill_in_text("Machine Learning", set(), "we use machine learning") is True


def test_get_adaptive_penalty_returns_safe_bounds():
    # No matching learning adjustment row -> default 1.0 (no crash)
    assert _get_adaptive_penalty({}, 999999, "Water and sanitation") == 1.0


# ---------------------------------------------------------------------------
# Public API of _classify still present (regression guard)
# ---------------------------------------------------------------------------
def test_classify_wrapper_is_stable():
    r = classify("water quality monitoring for contaminated borewell")
    # must expose the fields the rest of the app depends on
    for key in ("category", "confidence", "scores", "method"):
        assert key in r
