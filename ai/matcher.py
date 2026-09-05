import json
import re
from ai.embeddings import cosine, generate_embedding
from ai.skills import extract_skills
from database.db import get_db


def _g(row, key, default=""):
    """Safely read an optional column (schema may vary across DBs)."""
    try:
        v = row[key]
        return v if v is not None else default
    except Exception:
        return default


def _load_adjustments(db):
    """Load all adaptive penalty factors in a single query."""
    try:
        rows = db.execute(
            """SELECT university_id, category, penalty_factor
               FROM matcher_learning_adjustments WHERE sample_count >= 1"""
        ).fetchall()
    except Exception:
        return {}
    adj = {}
    for r in rows:
        adj[(r["university_id"], r["category"])] = max(0.5, min(1.0, r["penalty_factor"]))
    return adj


def _get_adaptive_penalty(adj, university_id, category):
    if (university_id, category) in adj:
        return adj[(university_id, category)]
    return adj.get((university_id, None), 1.0)


def _embedding_for(db, university, capability_text):
    """Embedding for a university's capability text.

    Uses the persisted universities.embedding_json when available; otherwise
    computes it once and writes it back so it is never recomputed per request.
    """
    emb_json = _g(university, "embedding_json", None)
    if emb_json:
        try:
            return json.loads(emb_json)
        except Exception:
            pass
    emb = generate_embedding(capability_text)
    if emb:
        try:
            db.execute(
                "UPDATE universities SET embedding_json=? WHERE id=?",
                (json.dumps(emb), university["id"]),
            )
        except Exception:
            pass  # non-critical; recompute next time
    return emb


def _data_fingerprint(db):
    """Cheap fingerprint of the tables that feed university profiles."""
    parts = []
    for t in ("faculty", "labs", "previous_projects", "institution_research_areas",
              "institution_facilities", "institution_programs"):
        try:
            r = db.execute(f"SELECT count(*) c, max(id) m FROM {t}").fetchone()
            parts.append(f"{r['c']}:{r['m']}")
        except Exception:
            parts.append("0")
    u = db.execute("SELECT count(*) c, max(id) m FROM universities").fetchone()
    parts.append(f"{u['c']}:{u['m']}")
    return "|".join(parts)


_PROFILES_CACHE = {}
_PROFILES_FP = None


def _load_profiles():
    """Static per-university matching data, cached across requests.

    The cache is keyed on a data fingerprint, so any change to universities,
    faculty, labs, projects, or research areas invalidates it automatically.
    Embeddings come from universities.embedding_json (persisted), so cache
    misses only re-read stored vectors instead of re-encoding.
    """
    global _PROFILES_FP, _PROFILES_CACHE
    with get_db() as db:
        fp = _data_fingerprint(db)
        if _PROFILES_FP == fp:
            return _PROFILES_CACHE
        profiles = _build_profiles(db)
        _PROFILES_FP = fp
        _PROFILES_CACHE = profiles
    return profiles


def _build_profiles(db):
    """Collect static per-university matching data in a handful of queries."""
    profiles = {}
    unis = db.execute("SELECT * FROM universities WHERE verified=1").fetchall()
    faculty = db.execute(
        "SELECT university_id, department, expertise FROM faculty").fetchall()
    labs = db.execute(
        "SELECT university_id, name, facilities FROM labs").fetchall()
    projects = db.execute(
        "SELECT university_id, title, description FROM previous_projects").fetchall()
    research = db.execute(
        "SELECT university_id, area, keywords FROM institution_research_areas").fetchall()
    facilities = db.execute(
        "SELECT university_id, name, type, capabilities FROM institution_facilities").fetchall()
    programs = db.execute(
        "SELECT university_id, name, department, focus FROM institution_programs").fetchall()

    def _group(rows):
        out = {}
        for r in rows:
            out.setdefault(r["university_id"], []).append(r)
        return out

    by_faculty = _group(faculty)
    by_labs = _group(labs)
    by_projects = _group(projects)
    by_research = _group(research)
    by_facilities = _group(facilities)
    by_programs = _group(programs)

    for uni in unis:
        uid = uni["id"]
        faculty_rows = by_faculty.get(uid, [])
        lab_rows = by_labs.get(uid, [])
        project_rows = by_projects.get(uid, [])
        research_rows = by_research.get(uid, [])
        facility_rows = by_facilities.get(uid, [])
        program_rows = by_programs.get(uid, [])

        faculty_text = " ".join(_g(x, "expertise") for x in faculty_rows)
        lab_text = " ".join(_g(x, "facilities") for x in lab_rows)
        project_text = " ".join(_g(x, "description") for x in project_rows)
        research_text = " ".join(
            f"{_g(x, 'area')} {_g(x, 'keywords')}" for x in research_rows)
        facility_text = " ".join(
            f"{_g(x, 'name')} {_g(x, 'type')} {_g(x, 'capabilities')}"
            for x in facility_rows)
        program_text = " ".join(
            f"{_g(x, 'name')} {_g(x, 'department')} {_g(x, 'focus')}"
            for x in program_rows)

        capability_text = (
            f"{_g(uni, 'description')} {_g(uni, 'expertise_summary')} "
            f"{_g(uni, 'research_summary')} {_g(uni, 'programs_summary')} "
            f"{_g(uni, 'facilities_summary')} {research_text} {program_text} "
            f"{facility_text} {faculty_text} {lab_text} {project_text}"
        )

        cap_lower = capability_text.lower()
        profiles[uid] = {
            "university_id": uid,
            "name": _g(uni, "name", f"University {uid}"),
            "capacity": _g(uni, "capacity", 0),
            "emb": _embedding_for(db, uni, capability_text),
            "cap_lower": cap_lower,
            "cap_words": set(re.findall(r"[a-z0-9]+", cap_lower)),
            "lab_words": set(re.findall(r"[a-z0-9]+", lab_text.lower())),
            "project_words": set(re.findall(r"[a-z0-9]+", project_text.lower())),
            "lab_lower": lab_text.lower(),
            "project_lower": project_text.lower(),
        }
    return profiles


CATEGORY_WORDS = {
    "water and sanitation": {"water", "sanitation", "hydrology", "drainage"},
    "healthcare": {"health", "medical", "hospital", "pharma", "clinical", "medicine"},
    "agriculture": {"agriculture", "farm", "crop", "soil", "irrigation", "agro"},
    "education": {"education", "learning", "teaching", "literacy", "school", "edtech"},
    "environment": {"environment", "pollution", "ecology", "biodiversity", "climate"},
    "infrastructure": {"infrastructure", "civil", "structural", "construction", "transport"},
    "waste management": {"waste", "garbage", "recycling", "landfill", "sewage"},
    "energy": {"energy", "solar", "renewable", "power", "electrical", "wind"},
    "transportation": {"transport", "traffic", "highway", "railway", "transit"},
    "employment": {"employment", "skill", "vocational", "training", "labour", "career"},
}


def _skill_in_text(skill, token_set, raw_text):
    """Check whether a skill phrase appears in a text.

    Multi-word skills (e.g. 'Machine Learning') match as substrings; single
    tokens match only as whole words to avoid false positives like 'AI' in
    'airport' or 'GIS' in 'begin'."""
    skill_lower = skill.lower()
    if " " in skill_lower:
        return skill_lower in raw_text
    return skill_lower in token_set


def match_universities(problem):
    required = set(extract_skills(problem["title"] + " " + problem["description"]))
    profiles = _load_profiles()
    with get_db() as db:
        adj = _load_adjustments(db)

    problem_emb = problem.get("embedding")
    category = (problem.get("category") or "").lower()
    cat_target = CATEGORY_WORDS.get(category, set())

    results = []
    for uid in profiles:
        uni = profiles[uid]
        uni_emb = uni["emb"]
        semantic = cosine(problem_emb, uni_emb) if uni_emb else 0.0

        skill_hits = sum(
            1 for skill in required
            if _skill_in_text(skill, uni["cap_words"], uni["cap_lower"]))
        skill_score = min(1.0, skill_hits / max(1, len(required))) if required else 0.5
        lab_score = min(
            1.0,
            sum(1 for skill in required
                if _skill_in_text(skill, uni["lab_words"], uni["lab_lower"]))
            / max(1, len(required)))
        project_score = min(
            1.0,
            sum(1 for skill in required
                if _skill_in_text(skill, uni["project_words"], uni["project_lower"]))
            / max(1, len(required)))

        capacity = uni["capacity"]
        try:
            capacity_score = min(1.0, max(0.0, float(capacity)) / 10)
        except (TypeError, ValueError):
            capacity_score = 0.0

        category_boost = 0.0
        if cat_target:
            hits = sum(1 for w in cat_target if w in uni["cap_words"])
            category_boost = min(0.20, hits * 0.05)

        final = (
            semantic * 0.50 +
            skill_score * 0.20 +
            lab_score * 0.10 +
            project_score * 0.10 +
            capacity_score * 0.10 +
            category_boost
        )

        penalty = _get_adaptive_penalty(adj, uid, problem.get("category"))
        final = final * penalty

        reasons = []
        if skill_score >= 0.5:
            reasons.append("relevant faculty expertise")
        if lab_score >= 0.4:
            reasons.append("matching laboratory capability")
        if project_score >= 0.4:
            reasons.append("related previous projects")
        if capacity_score >= 0.7:
            reasons.append("available capacity")
        if category_boost >= 0.10:
            reasons.append("strong category alignment with problem domain")
        if semantic >= 0.5:
            reasons.append(f"semantic match strength {round(semantic * 100)}%")
        if penalty < 0.95:
            reasons.append(
                f"trust adjusted (decline history, factor {round(penalty, 2)})")

        results.append({
            "university_id": uni["university_id"],
            "university": uni["name"],
            "semantic_score": round(semantic, 4),
            "skill_score": round(skill_score, 4),
            "lab_score": round(lab_score, 4),
            "project_score": round(project_score, 4),
            "capacity_score": round(capacity_score, 4),
            "final_score": round(final, 4),
            "match_percent": round(final * 100, 1),
            "skills_used": sorted(required),
            "explanation": reasons or ["general semantic capability match"],
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    for rank, result in enumerate(results, start=1):
        result["rank"] = rank

    return results