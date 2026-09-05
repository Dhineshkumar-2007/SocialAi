# Keyword-based scoring factors
SEVERITY_KEYWORDS = {
    "critical": [
        "death", "died", "dead", "killed", "fatal", "lifethreatening",
        "dangerous", "unsafe", "contamination", "toxic", "poison",
        "hospital", "icu", "emergency", "fire", "explosion", "collapse",
        "stray", "bite", "attack", "dog", "animal",
    ],
    "high": [
        "health", "flood", "flooding", "accident", "school", "water",
        "sick", "illness", "disease", "injury", "injured",
        "crack", "structural", "hazard", "blocked",
        "power cut", "blackout", "outage", "electrical",
    ],
    "medium": [
        "poor", "broken", "damaged", "malfunction", "leak", "sewage",
        "garbage", "waste", "unemployment", "congestion",
    ],
}

POPULATION_KEYWORDS = {
    "village": 80, "district": 85, "community": 75,
    "town": 55, "city": 60, "municipal": 60,
    "many families": 80, "hundreds": 80, "thousands": 90,
    "50,000": 85, "10,000": 75, "5,000": 65,
    "500": 65, "300": 60, "200": 55, "children": 70, "school": 70,
}

SAFETY_KEYWORDS = {
    "death": 95, "died": 95, "killed": 95, "fatal": 95,
    "dying": 95, "poison": 95, "explosion": 95,
    "toxic": 90, "fire": 90, "dangerous": 90, "unsafe": 90,
    "danger": 90, "accident": 85, "injury": 85, "injured": 85,
    "attack": 85, "contamination": 80, "hospital": 70, "emergency": 80,
    "illness": 75, "disease": 75,
}

URGENCY_KEYWORDS = {
    "urgent": 30, "immediate": 30, "asap": 20, "critical": 25,
    "severe": 15, "chronic": 10, "ongoing": 5, "months": 15,
    "years": 20, "weeks": 15, "stopped": 20, "failed": 15,
    "risk": 15, "daily": 10, "illness": 10, "contamination": 15,
    "poison": 15, "toxic": 10, "unsafe": 10, "collapse": 20, "danger": 10,
}


def calculate_priority(problem, evidence_score=0.0, duplicate_count=0):
    """Calculate priority score with multi-factor analysis.

    Components (sum to 100):
      - severity: 0-100 based on keyword matching (35%)
      - population: 0-100 based on affected population keywords (20%)
      - evidence: 0-100 from AI evidence score (20%)
      - reports: 0-100 based on duplicate count (10%)
      - safety: 0-100 based on danger keywords (15%)

    Level thresholds:
      critical: score >= 75
      high:     score >= 55
      medium:   score >= 35
      low:      score < 35
    """
    text = (
        str(problem.get("title", "")) + " " +
        str(problem.get("description", ""))
    ).lower()

    # --- Severity (base 50, keyword boost; critical hits get +10) ---
    severity = 50
    critical_hits = sum(1 for x in SEVERITY_KEYWORDS["critical"] if x in text)
    high_hits = sum(1 for x in SEVERITY_KEYWORDS["high"] if x in text)
    medium_hits = sum(1 for x in SEVERITY_KEYWORDS["medium"] if x in text)
    if critical_hits > 0:
        severity = 100
    elif high_hits > 0:
        severity = 85
    elif medium_hits > 0:
        severity = 65
    # Add small bonus for multiple critical keywords
    severity = min(100, severity + critical_hits * 5)

    # --- Population Impact (base 40, keyword boost) ---
    population = 40
    for keyword, score in sorted(POPULATION_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in text:
            population = max(population, score)
            break

    # --- Safety Risk (base 30, keyword boost) ---
    safety = 30
    for keyword, score in sorted(SAFETY_KEYWORDS.items(), key=lambda x: -score):
        if keyword in text:
            safety = max(safety, score)
            break

    # --- Urgency Boost ---
    urgency_boost = 0
    for keyword, score in URGENCY_KEYWORDS.items():
        if keyword in text:
            urgency_boost = max(urgency_boost, score)

    # --- Reports (duplicate count) ---
    reports = min(100, 30 + duplicate_count * 20)

    # --- Evidence gap bonus: critical problems without evidence need a boost ---
    # Without evidence, max possible score is ~64.5 — below the critical threshold.
    # Critical-severity problems without evidence get a +15 bump to cross 75.
    evidence_gap_bonus = 15 if (severity >= 100 and evidence_score == 0) else 0

    # --- Combined Score ---
    score = (
        severity * 0.35 +
        population * 0.20 +
        evidence_score * 0.20 +
        reports * 0.10 +
        safety * 0.15 +
        urgency_boost * 0.05 +
        evidence_gap_bonus
    )

    score = round(min(100, score), 2)
    level = (
        "critical" if score >= 75 else
        "high" if score >= 55 else
        "medium" if score >= 35 else
        "low"
    )

    return {
        "score": score,
        "level": level,
        "factors": {
            "severity": severity,
            "population": population,
            "evidence": evidence_score,
            "reports": reports,
            "safety": safety,
            "urgency_boost": urgency_boost,
            "evidence_gap_bonus": evidence_gap_bonus,
        }
    }
