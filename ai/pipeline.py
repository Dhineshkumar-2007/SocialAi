import json
import os
from ai.embeddings import generate_embedding
from ai.classifier import classify
from ai.skills import extract_skills
from ai.priority import calculate_priority
from ai.duplicate import find_duplicates
from ai.vision import analyze_image
from ai.matcher import match_universities
from services.industry_matcher import match_industry
from database.db import get_db


def _row_to_dict(row):
    return dict(row)


def analyze_problem(problem_id):
    """Run full AI analysis pipeline for a problem.

    Always runs all stages. The matcher is NOT gated by evidence score
    because real problems with weak evidence should still be matchable.
    """
    with get_db() as db:
        row = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not row:
            return None

        problem = _row_to_dict(row)
        text = f"{problem['title']}. {problem['description']}"

        embedding = generate_embedding(text)
        classification = classify(text)
        skills = extract_skills(text)

        evidence_rows = db.execute(
            "SELECT * FROM evidence WHERE problem_id=?", (problem_id,)
        ).fetchall()

        evidence_results = []
        evidence_score = 0.0
        for e in evidence_rows:
            if e["caption"] and e["evidence_status"] not in ("pending", "error", "disabled"):
                # Already analyzed by a previous run — reuse instead of
                # re-running the (~1.7s) BLIP caption + embedding pass.
                result = {
                    "caption": e["caption"],
                    "supports_report": bool(e["supports_report"]),
                    "confidence": float(e["confidence"] or 0),
                    "similarity": float(e["relevance"] or 0),
                    "title_relevance": float(e["title_relevance"] or 0),
                    "description_relevance": float(e["description_relevance"] or 0),
                    "image_relevance": float(e["image_relevance"] or e["relevance"] or 0),
                    "evidence_status": e["evidence_status"],
                }
            else:
                path = os.path.join("uploads", e["filename"])
                result = analyze_image(path, text, problem["title"], problem["description"]) if os.path.exists(path) else {
                    "caption": "Evidence file unavailable",
                    "supports_report": False,
                    "confidence": 0,
                    "evidence_status": "error"
                }
            evidence_results.append({
                "id": e["id"],
                "filename": e["filename"],
                **result
            })
            db.execute("""UPDATE evidence SET caption=?, supports_report=?, confidence=?, evidence_status=?, relevance=?, title_relevance=?, description_relevance=?, image_relevance=? WHERE id=?""", (
                result.get("caption"), 1 if result.get("supports_report") else 0,
                result.get("confidence", 0), result.get("evidence_status", "pending"),
                result.get("image_relevance", result.get("similarity", 0)),
                result.get("title_relevance", 0), result.get("description_relevance", 0),
                result.get("image_relevance", result.get("similarity", 0)), e["id"]))
            # Only contributing evidence boosts the score
            if result.get("evidence_status") in ("supporting", "uncertain"):
                evidence_score = max(evidence_score, float(result.get("confidence", 0)))

        problem["embedding"] = embedding

        others = []
        rows = db.execute(
            "SELECT * FROM problems WHERE id != ?", (problem_id,)
        ).fetchall()
        for r in rows:
            d = _row_to_dict(r)
            if d.get("embedding_json"):
                try:
                    d["embedding"] = json.loads(d["embedding_json"])
                except Exception:
                    d["embedding"] = None
            others.append(d)

        duplicates = find_duplicates(problem, others)
        priority = calculate_priority(
            problem,
            evidence_score * 100,
            len(duplicates)
        )

        db.execute("""
            UPDATE problems
            SET category=?, priority_score=?, priority_level=?,
                evidence_score=?, evidence_caption=?, skills_json=?,
                embedding_json=?, status=?
            WHERE id=?
        """, (
            classification["category"],
            priority["score"],
            priority["level"],
            evidence_score * 100,
            evidence_results[0]["caption"] if evidence_results else None,
            json.dumps(skills),
            json.dumps(embedding) if embedding else None,
            "analyzed",
            problem_id
        ))

        db.execute("DELETE FROM problem_links WHERE problem_id=?", (problem_id,))
        for d in duplicates:
            db.execute("""
                INSERT INTO problem_links(problem_id,similar_problem_id,similarity,distance_km,category_match)
                VALUES(?,?,?,?,?)
            """, (
                problem_id, d["problem_id"],
                d["similarity"], d["distance_km"],
                1 if d.get("category_match") else 0
            ))

    # Run matching OUTSIDE the write transaction: the matcher opens its own
    # DB connections (and persists university embeddings), so keeping it inside
    # the transaction above would hold the write lock for the whole pass.
    problem["embedding"] = embedding
    matches = match_universities(problem)
    industry_matches = match_industry(text, embedding)

    # Apply evidence reliability discount to match scores if evidence is weak
    if evidence_score < 0.4:
        for m in matches:
            m["final_score"] = round(m["final_score"] * 0.7, 4)
            m["match_percent"] = round(m["final_score"] * 100, 1)
        for m in industry_matches:
            m["final_score"] = round(m["final_score"] * 0.7, 4)
            m["match_percent"] = round(m["final_score"] * 100, 1)

    with get_db() as db:
        # Main store per assignment-system spec (with rank)
        db.execute("DELETE FROM problem_university_matches WHERE problem_id=?", (problem_id,))
        for rank, m in enumerate(matches, start=1):
            db.execute("""
                INSERT INTO problem_university_matches(
                    problem_id, university_id, semantic_score, skill_score,
                    lab_score, project_score, capacity_score, final_score,
                    explanation, rank
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (
                problem_id, m["university_id"], m["semantic_score"],
                m["skill_score"], m["lab_score"], m["project_score"],
                m["capacity_score"], m["final_score"],
                json.dumps(m["explanation"]), rank
            ))
        # Backward-compat: also keep legacy `matches` alive for existing routes
        db.execute("DELETE FROM matches WHERE problem_id=?", (problem_id,))
        for rank, m in enumerate(matches, start=1):
            db.execute("""
                INSERT INTO matches(
                    problem_id, university_id, semantic_score, skill_score,
                    lab_score, project_score, capacity_score, final_score, explanation
                ) VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                problem_id, m["university_id"], m["semantic_score"],
                m["skill_score"], m["lab_score"], m["project_score"],
                m["capacity_score"], m["final_score"],
                json.dumps(m["explanation"])
            ))

        db.execute("DELETE FROM industry_matches WHERE problem_id=?", (problem_id,))
        for m in industry_matches:
            db.execute("""
                INSERT INTO industry_matches(
                    problem_id, industry_id, semantic_score, skill_score,
                    sector_score, final_score, explanation
                ) VALUES(?,?,?,?,?,?,?)
            """, (
                problem_id, m["industry_id"], m["semantic_score"],
                m["skill_score"], m["sector_score"], m["final_score"],
                json.dumps(m["explanation"])
            ))

    return {
        "problem_id": problem_id,
        "classification": classification,
        "skills": skills,
        "evidence": evidence_results,
        "duplicates": duplicates,
        "priority": priority,
        "matches": matches,
        "industry_matches": industry_matches,
    }
