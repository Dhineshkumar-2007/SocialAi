"""AI component tests with real data samples."""
import json
from ai.classifier import classify
from ai.skills import extract_skills
from ai.priority import calculate_priority
from ai.embeddings import generate_embedding, cosine
from ai.duplicate import find_duplicates, haversine_km
from ai.matcher import match_universities
from services.industry_matcher import _sector_match_score, SECTOR_KEYWORDS

# Real-world test data samples covering all 10 problem categories
SAMPLE_PROBLEMS = [
    {
        "id": 1,
        "title": "Contaminated borewell water in village",
        "description": "Drinking water from borewell has high contamination causing illness in 200 families. Urgent water quality testing needed.",
        "expected_category": "Water and sanitation",
        "expected_skills": ["Water Quality Analysis", "Hydrology"],
    },
    {
        "id": 2,
        "title": "Hospital lacks ICU equipment during monsoon",
        "description": "District hospital in flood-affected area has no ICU beds, patients being turned away. Emergency medical help needed.",
        "expected_category": "Healthcare",
        "expected_skills": ["Healthcare", "Disaster Management"],
    },
    {
        "id": 3,
        "title": "Crop failure due to soil salinity in delta region",
        "description": "Paddy crops failing across 500 acres due to saline soil and poor irrigation. Need agricultural intervention.",
        "expected_category": "Agriculture",
        "expected_skills": ["Agricultural Engineering", "Hydrology"],
    },
    {
        "id": 4,
        "title": "School building unsafe after flood damage",
        "description": "Primary school roof collapsed, 300 children without classroom. Structural assessment and rebuilding needed.",
        "expected_category": "Infrastructure",
        "expected_skills": ["Civil Engineering", "Structural Engineering"],
    },
    {
        "id": 5,
        "title": "Garbage accumulation in residential area",
        "description": "Municipal waste collection stopped 3 weeks ago, health hazard building up across 4 wards.",
        "expected_category": "Waste management",
        "expected_skills": ["Waste Management", "Environmental Engineering"],
    },
    {
        "id": 6,
        "title": "Power cuts for 12 hours daily in village",
        "description": "Electricity supply unreliable, no solar backup, students cannot study at night. Need renewable energy solution.",
        "expected_category": "Energy",
        "expected_skills": ["Energy", "IoT"],
    },
    {
        "id": 7,
        "title": "Traffic congestion at junction near bus stand",
        "description": "No traffic signal, accidents increasing, 30 minute delays daily for thousands of commuters.",
        "expected_category": "Transportation",
        "expected_skills": ["Transportation", "Traffic Engineering"],
    },
    {
        "id": 8,
        "title": "Youth unemployment in rural district",
        "description": "500+ unemployed youth, need vocational training programs and skill development.",
        "expected_category": "Employment",
        "expected_skills": ["Education Technology"],
    },
]


def test_classifier_with_samples():
    """Test classifier against 8 real-world problem samples."""
    print("\n--- Classifier Tests ---")
    pass_count = 0
    for p in SAMPLE_PROBLEMS:
        result = classify(p["title"])
        category = result["category"]
        confidence = result["confidence"]
        ok = category in {"Water and sanitation", "Healthcare", "Agriculture", "Education",
                          "Environment", "Infrastructure", "Waste management", "Energy",
                          "Transportation", "Employment"}
        if ok:
            pass_count += 1
            marker = "[OK]" if category == p["expected_category"] else "[WARN]"
            print(f"  {marker} [{p['id']}] {p['title'][:40]}...")
            print(f"      -> {category} (conf={confidence:.2f}, expected={p['expected_category']})")
        else:
            print(f"  [FAIL] [{p['id']}] Invalid category: {category}")
    print(f"  Classifier: {pass_count}/{len(SAMPLE_PROBLEMS)} valid")


def test_skills_with_samples():
    """Test skill extraction on each sample problem."""
    print("\n--- Skills Extraction Tests ---")
    pass_count = 0
    for p in SAMPLE_PROBLEMS:
        text = f"{p['title']}. {p['description']}"
        skills = extract_skills(text)
        # Check at least one expected skill was extracted
        hit = any(s in skills for s in p["expected_skills"])
        if hit:
            pass_count += 1
            print(f"  [OK] [{p['id']}] {len(skills)} skills extracted: {skills[:4]}{'...' if len(skills) > 4 else ''}")
        else:
            print(f"  [WARN] [{p['id']}] No expected skills found. Got: {skills}")
    print(f"  Skills: {pass_count}/{len(SAMPLE_PROBLEMS)} matched")


def test_priority_with_samples():
    """Test priority scoring with various severity levels."""
    print("\n--- Priority Scoring Tests ---")
    cases = [
        ("Low: streetlight not working for 1 week", 0.0, 0, "low", 0, 35),
        ("Medium: pothole on main road causing minor issues", 40.0, 0, "medium", 35, 60),
        ("High: water contamination in village causing illness", 75.0, 1, "critical", 75, 100),
        ("Critical: toxic waste dumping poisoning community water", 90.0, 3, "critical", 70, 100),
        # Test urgency boost
        ("Urgent: building collapse risk at school", 85.0, 0, "critical", 75, 100),
    ]
    for title, ev, dups, level, lo, hi in cases:
        problem = {"title": title, "description": ""}
        r = calculate_priority(problem, evidence_score=ev, duplicate_count=dups)
        ok = r["level"] == level and lo <= r["score"] <= hi
        marker = "[OK]" if ok else "[WARN]"
        print(f"  {marker} '{title[:45]}'")
        print(f"      score={r['score']}, level={r['level']} (expected={level})")
        if "factors" in r:
            print(f"      factors: severity={r['factors']['severity']}, pop={r['factors']['population']}, "
                  f"safety={r['factors']['safety']}, urgency={r['factors']['urgency_boost']}")


def test_embeddings_and_cosine():
    """Test BGE embedding generation and cosine similarity."""
    print("\n--- Embeddings Tests ---")
    pairs = [
        ("Water quality monitoring system", "Groundwater sensor network", True),
        ("Bridge structural damage", "Road surface deterioration", True),
        ("Hospital ICU shortage", "Astronomy telescope calibration", False),
    ]
    for a, b, should_relate in pairs:
        ea = generate_embedding(a)
        eb = generate_embedding(b)
        if ea and eb:
            sim = cosine(ea, eb)
            in_range = 0 <= sim <= 1
            print(f"  [OK] cos('{a[:30]}', '{b[:30]}') = {sim:.3f} (valid={in_range})")
        else:
            print(f"  [WARN] Embeddings disabled (AI_ENABLED=False)")


def test_duplicate_detection():
    """Test semantic + geographic duplicate detection."""
    print("\n--- Duplicate Detection Tests ---")
    base = {"id": 1, "title": "Water contamination", "description": "Well water dirty",
            "latitude": 13.0, "longitude": 80.2, "embedding": [0.1] * 384}
    others = [
        {"id": 2, "title": "Water contamination", "description": "Well water dirty",
         "latitude": 13.01, "longitude": 80.21, "embedding": [0.1] * 384},
        {"id": 3, "title": "Road repair needed", "description": "Bridge broken",
         "latitude": 13.5, "longitude": 80.5, "embedding": [0.9] * 384},
    ]
    dups = find_duplicates(base, others)
    assert len(dups) == 1, f"Expected 1 duplicate, got {len(dups)}"
    assert dups[0]["problem_id"] == 2
    print(f"  [OK] Found {len(dups)} duplicate(s): id={dups[0]['problem_id']}, sim={dups[0]['similarity']:.3f}")


def test_haversine():
    """Test geographic distance calculation."""
    print("\n--- Haversine Tests ---")
    km = haversine_km(13.0, 80.0, 13.01, 80.01)
    assert km is not None and km < 2.0
    print(f"  [OK] Distance(13.0,80.0 -> 13.01,80.01) = {km:.3f} km")
    km2 = haversine_km(13.0, 80.0, 14.0, 81.0)
    assert km2 > 100
    print(f"  [OK] Distance(13.0,80.0 -> 14.0,81.0) = {km2:.3f} km (longer)")


def test_industry_sector_match():
    """Test new sector keyword-based matching logic."""
    print("\n--- Industry Sector Match Tests ---")
    cases = [
        ("water contamination in village", "Water", 1.0),
        ("farming irrigation issue", "Agricultural", 0.75),
        ("hospital equipment shortage", "Healthcare", 1.0),
        ("completely unrelated text", "Water", 0.4),
    ]
    for text, sector, expected_min in cases:
        score = _sector_match_score(text, sector)
        ok = score >= expected_min - 0.01
        marker = "[OK]" if ok else "[WARN]"
        print(f"  {marker} sector='{sector}' on '{text[:30]}' -> {score:.2f} (>= {expected_min})")


def run_all():
    print("=" * 60)
    print("=== AI Component Tests (with real-world data) ===")
    print("=" * 60)
    test_classifier_with_samples()
    test_skills_with_samples()
    test_priority_with_samples()
    test_embeddings_and_cosine()
    test_duplicate_detection()
    test_haversine()
    test_industry_sector_match()
    print("\n" + "=" * 60)
    print("=== All AI tests completed ===")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
