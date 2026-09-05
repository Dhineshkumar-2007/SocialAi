import json
from ai.embeddings import cosine
from ai.skills import extract_skills
from database.db import get_db


def _get_adaptive_penalty(db, university_id, category):
    """Look up adaptive penalty factor from the learning loop table.

    Returns a multiplier in [0.5, 1.0] based on prior decline reasons.
    If no adjustment exists, returns 1.0 (no penalty).
    """
    try:
        row = db.execute(
            """SELECT penalty_factor, sample_count FROM matcher_learning_adjustments
               WHERE university_id=? AND (category=? OR category IS NULL)
               ORDER BY sample_count DESC LIMIT 1""",
            (university_id, category)
        ).fetchone()
        if row and row["sample_count"] >= 1:
            return max(0.5, min(1.0, row["penalty_factor"]))
    except Exception:
        pass
    return 1.0


def _text_for_university(db, uid):
    faculty = db.execute("SELECT * FROM faculty WHERE university_id=?", (uid,)).fetchall()
    labs = db.execute("SELECT * FROM labs WHERE university_id=?", (uid,)).fetchall()
    projects = db.execute("SELECT * FROM previous_projects WHERE university_id=?", (uid,)).fetchall()
    parts = []
    for x in faculty:
        parts.append(f"{x['department']} {x['expertise']}")
    for x in labs:
        parts.append(f"{x['name']} {x['facilities']}")
    for x in projects:
        parts.append(f"{x['title']} {x['description']}")
    return " ".join(parts)

def match_universities(problem):
    required = set(extract_skills(problem["title"] + " " + problem["description"]))
    with get_db() as db:
        universities = db.execute("SELECT * FROM universities").fetchall()
        results = []

        for u in universities:
            uid = u["id"]
            faculty = db.execute("SELECT * FROM faculty WHERE university_id=?", (uid,)).fetchall()
            labs = db.execute("SELECT * FROM labs WHERE university_id=?", (uid,)).fetchall()
            projects = db.execute("SELECT * FROM previous_projects WHERE university_id=?", (uid,)).fetchall()

            faculty_text = " ".join(x["expertise"] for x in faculty)
            lab_text = " ".join(x["facilities"] for x in labs)
            project_text = " ".join(x["description"] for x in projects)

            capability_text = f"{u['description']} {faculty_text} {lab_text} {project_text}"

            from ai.embeddings import generate_embedding
            uni_emb = generate_embedding(capability_text)
            semantic = cosine(problem.get("embedding"), uni_emb) if uni_emb else 0.0

            cap_words = capability_text.lower()
            skill_hits = sum(1 for skill in required if skill.lower() in cap_words)
            skill_score = min(1.0, skill_hits / max(1, len(required))) if required else 0.5
            lab_score = min(1.0, sum(1 for skill in required if skill.lower() in lab_text.lower()) / max(1, len(required)))
            project_score = min(1.0, sum(1 for skill in required if skill.lower() in project_text.lower()) / max(1, len(required)))
            capacity_score = min(1.0, max(0, u["capacity"]) / 10)

            final = (
                semantic * 0.40 +
                skill_score * 0.25 +
                lab_score * 0.15 +
                project_score * 0.10 +
                capacity_score * 0.10
            )

            # Apply adaptive learning penalty from previous decline feedback
            category = problem.get("category")
            penalty = _get_adaptive_penalty(db, uid, category)
            final = final * penalty

            reasons = []
            if skill_score >= 0.5: reasons.append("relevant faculty expertise")
            if lab_score >= 0.4: reasons.append("matching laboratory capability")
            if project_score >= 0.4: reasons.append("related previous projects")
            if capacity_score >= 0.7: reasons.append("available capacity")

            results.append({
                "university_id": uid,
                "university": u["name"],
                "semantic_score": round(semantic, 4),
                "skill_score": round(skill_score, 4),
                "lab_score": round(lab_score, 4),
                "project_score": round(project_score, 4),
                "capacity_score": round(capacity_score, 4),
                "final_score": round(final, 4),
                "match_percent": round(final * 100, 1),
                "skills_used": sorted(required),
                "explanation": reasons or ["general semantic capability match"]
            })

        results.sort(key=lambda x: x["final_score"], reverse=True)

        # Add rank numbering to results
        for rank, result in enumerate(results, start=1):
            result["rank"] = rank

        return results
