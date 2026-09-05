import math
from ai.embeddings import cosine
from config import Config

def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * r * math.asin(math.sqrt(a))

def find_duplicates(problem, all_problems):
    results = []
    emb = problem.get("embedding")
    for other in all_problems:
        if other["id"] == problem["id"] or not other.get("embedding"):
            continue
        semantic = cosine(emb, other["embedding"])
        distance = haversine_km(
            problem.get("latitude"), problem.get("longitude"),
            other.get("latitude"), other.get("longitude")
        )
        # Soft geo signal: full credit <=2km, linearly decay to 0 at 20km
        if distance is None:
            geo = 0.0
        elif distance <= 2.0:
            geo = 1.0
        elif distance >= 20.0:
            geo = 0.0
        else:
            geo = 1.0 - (distance - 2.0) / 18.0
        # Category agreement further reinforces duplicate signal
        same_cat = 1.0 if (problem.get("category") and
                           problem.get("category") == other.get("category")) else 0.0
        score = semantic * 0.70 + geo * 0.15 + same_cat * 0.15
        if score >= Config.DUPLICATE_THRESHOLD:
            results.append({
                "problem_id": other["id"],
                "similarity": round(score, 4),
                "semantic_similarity": round(semantic, 4),
                "distance_km": None if distance is None else round(distance, 3),
                "category_match": bool(same_cat),
            })
    return sorted(results, key=lambda x: x["similarity"], reverse=True)
