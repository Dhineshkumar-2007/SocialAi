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
        geo = 1.0 if distance is not None and distance <= 2 else 0.0
        score = semantic * 0.80 + geo * 0.20
        if score >= Config.DUPLICATE_THRESHOLD:
            results.append({
                "problem_id": other["id"],
                "similarity": round(score, 4),
                "semantic_similarity": round(semantic, 4),
                "distance_km": None if distance is None else round(distance, 3)
            })
    return sorted(results, key=lambda x: x["similarity"], reverse=True)
