"""Industry matching service."""
import json, re
from ai.embeddings import generate_embedding, cosine
from ai.skills import extract_skills
from models.industry_partner import IndustryPartner


# Sector keyword mapping for more reliable sector matching
SECTOR_KEYWORDS = {
    "Water": {"water", "sewage", "sanitation", "drainage", "well", "borewell", "groundwater"},
    "Agricultural": {"agriculture", "farm", "crop", "irrigation", "soil", "livestock", "farming"},
    "Automotive": {"transport", "vehicle", "traffic", "mobility", "road"},
    "Infrastructure": {"road", "bridge", "building", "construction", "civil"},
    "IT Services": {"education", "literacy", "digital", "technology", "computer"},
    "Government": {"government", "public", "policy", "municipal", "civic"},
    "Healthcare": {"health", "hospital", "medical", "disease", "clinic"},
    "Energy": {"energy", "electricity", "solar", "power", "renewable"},
}


def _sector_match_score(problem_text, sector):
    """Compute how well a problem text matches a sector based on keywords."""
    if not problem_text or not sector:
        return 0.5
    text_lower = problem_text.lower()
    sector_lower = sector.lower()
    # Direct sector name match
    if sector_lower in text_lower:
        return 1.0
    # Keyword-based match
    keywords = SECTOR_KEYWORDS.get(sector, set())
    if keywords:
        hits = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
        if hits > 0:
            return min(1.0, 0.5 + 0.25 * hits)
    return 0.4  # baseline if no match


def match_industry(problem_text, problem_embedding=None):
    """Match a problem against industry partners using hybrid ranking.

    Improved scoring:
      - semantic  * 0.50  (BGE embedding similarity)
      - skill     * 0.25  (extracted skill keyword overlap)
      - sector    * 0.25  (sector-to-problem keyword match)
    """
    required = set(extract_skills(problem_text))
    partners = IndustryPartner.list_all()
    results = []
    if problem_embedding is None:
        problem_embedding = generate_embedding(problem_text)

    persist = {}
    for p in partners:
        cap_text = f"{p.name} {p.sector} {p.capabilities_text}"
        if p.embedding_json:
            try:
                p_emb = json.loads(p.embedding_json)
            except Exception:
                p_emb = generate_embedding(cap_text)
        else:
            p_emb = generate_embedding(cap_text)
            if p_emb:
                # Compute once, then persist so later requests skip the encode.
                persist[p.id] = json.dumps(p_emb)

        semantic = cosine(problem_embedding, p_emb) if (problem_embedding and p_emb) else 0.0

        cap_words = cap_text.lower()
        skill_hits = sum(1 for s in required if s.lower() in cap_words)
        skill_score = min(1.0, skill_hits / max(1, len(required))) if required else 0.5
        sector_score = _sector_match_score(problem_text, p.sector)

        final = semantic * 0.50 + skill_score * 0.25 + sector_score * 0.25
        results.append({
            'industry_id': p.id,
            'industry': p.name,
            'sector': p.sector,
            'semantic_score': round(semantic, 4),
            'skill_score': round(skill_score, 4),
            'sector_score': round(sector_score, 4),
            'final_score': round(final, 4),
            'match_percent': round(final * 100, 1),
            'explanation': [
                f"Industry sector: {p.sector}" if final > 0.6 else f"Sector match for {p.sector}",
                f"Capability overlap on required skills" if skill_score > 0.4 else "General capability match"
            ],
        })

    results.sort(key=lambda x: x['final_score'], reverse=True)

    if persist:
        try:
            from database.db import get_db
            with get_db() as db:
                for pid, emb in persist.items():
                    db.execute(
                        "UPDATE industry_partners SET embedding_json=? WHERE id=?",
                        (emb, pid))
        except Exception:
            pass

    return results[:5]
