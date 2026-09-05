def calculate_priority(problem, evidence_score=0.0, duplicate_count=0):
    text = (
        str(problem.get("title", "")) + " " +
        str(problem.get("description", ""))
    ).lower()

    severity = 40
    if any(x in text for x in ["death", "danger", "unsafe", "contamination", "hospital", "fire"]):
        severity = 90
    elif any(x in text for x in ["health", "flood", "accident", "school", "water"]):
        severity = 75

    population = 70 if any(
        x in text for x in ["village", "community", "many families", "hundreds", "district"]
    ) else 45

    safety = 80 if any(
        x in text for x in ["danger", "unsafe", "accident", "contamination", "fire"]
    ) else 40

    reports = min(100, 40 + duplicate_count * 15)

    score = (
        severity * 0.35 +
        population * 0.20 +
        evidence_score * 0.20 +
        reports * 0.10 +
        safety * 0.15
    )

    score = round(min(100, score), 2)
    level = "critical" if score >= 81 else "high" if score >= 66 else "medium" if score >= 41 else "low"

    return {"score": score, "level": level}
