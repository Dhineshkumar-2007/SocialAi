"""Industry matching service."""
from ai.embeddings import generate_embedding, cosine
from ai.skills import extract_skills
from models.industry_partner import IndustryPartner


def match_industry(problem_text, problem_embedding=None):
    """Match a problem against industry partners using hybrid ranking."""
    required = set(extract_skills(problem_text))
    partners = IndustryPartner.list_all()
    results = []
    if problem_embedding is None:
        problem_embedding = generate_embedding(problem_text)

    for p in partners:
        cap_text = f"{p.name} {p.sector} {p.capabilities_text}"
        if p.embedding_json:
            try:
                import json
                p_emb = json.loads(p.embedding_json)
            except Exception:
                p_emb = generate_embedding(cap_text)
        else:
            p_emb = generate_embedding(cap_text)

        semantic = cosine(problem_embedding, p_emb) if (problem_embedding and p_emb) else 0.0

        cap_words = cap_text.lower()
        skill_hits = sum(1 for s in required if s.lower() in cap_words)
        skill_score = min(1.0, skill_hits / max(1, len(required))) if required else 0.5
        sector_score = 1.0 if any(s.lower() in cap_words for s in (problem_text or '').lower().split()) else 0.5

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
    return results[:5]
