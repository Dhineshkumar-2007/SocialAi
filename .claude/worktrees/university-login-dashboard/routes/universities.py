from flask import Blueprint, request, jsonify
from database.db import get_db

universities_bp = Blueprint("universities", __name__, url_prefix="/api/universities")

@universities_bp.get("")
def list_universities():
    with get_db() as db:
        rows = db.execute("SELECT * FROM universities ORDER BY name").fetchall()
        result = []
        for u in rows:
            x = dict(u)
            x["faculty"] = [dict(r) for r in db.execute(
                "SELECT * FROM faculty WHERE university_id=?", (u["id"],)
            ).fetchall()]
            x["labs"] = [dict(r) for r in db.execute(
                "SELECT * FROM labs WHERE university_id=?", (u["id"],)
            ).fetchall()]
            x["projects"] = [dict(r) for r in db.execute(
                "SELECT * FROM previous_projects WHERE university_id=?", (u["id"],)
            ).fetchall()]
            result.append(x)
        return jsonify(result)

@universities_bp.post("")
def create_university():
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    with get_db() as db:
        cur = db.execute("""
            INSERT INTO universities(name,city,description,capacity)
            VALUES(?,?,?,?)
        """, (
            data["name"], data.get("city"),
            data.get("description", ""),
            data.get("capacity", 10)
        ))
        uid = cur.lastrowid

        for f in data.get("faculty", []):
            db.execute("""
                INSERT INTO faculty(university_id,name,department,expertise)
                VALUES(?,?,?,?)
            """, (uid, f["name"], f.get("department"), f.get("expertise", "")))

        for l in data.get("labs", []):
            db.execute("""
                INSERT INTO labs(university_id,name,facilities)
                VALUES(?,?,?)
            """, (uid, l["name"], l.get("facilities", "")))

        for p in data.get("projects", []):
            db.execute("""
                INSERT INTO previous_projects(university_id,title,description)
                VALUES(?,?,?)
            """, (uid, p["title"], p.get("description", "")))

    return jsonify({"message": "university created", "id": uid}), 201
