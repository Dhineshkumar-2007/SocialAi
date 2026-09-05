import os, uuid, json
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from database.db import get_db
from ai.pipeline import analyze_problem
from services.assignment_service import auto_assign_top_university

problems_bp = Blueprint("problems", __name__, url_prefix="/api/problems")

@problems_bp.post("")
def create_problem():
    title = request.form.get("title")
    description = request.form.get("description")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    # Fall back to JSON body for API-only callers (no file upload)
    if not title:
        payload = request.get_json(silent=True) or {}
        title = payload.get("title")
        description = payload.get("description")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")

    if not title or not description:
        return jsonify({"error": "title and description are required"}), 400

    try:
        latitude = float(latitude) if latitude is not None else None
        longitude = float(longitude) if longitude is not None else None
    except ValueError:
        return jsonify({"error": "latitude/longitude must be numeric"}), 400

    with get_db() as db:
        cur = db.execute("""
            INSERT INTO problems(title,description,latitude,longitude)
            VALUES(?,?,?,?)
        """, (title, description, latitude, longitude))
        problem_id = cur.lastrowid

        uploaded = request.files.getlist("evidence")
        for file in uploaded:
            if not file or not file.filename:
                continue
            name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)
            file.save(os.path.join(current_app.config["UPLOAD_DIR"], name))
            db.execute(
                "INSERT INTO evidence(problem_id,filename) VALUES(?,?)",
                (problem_id, name)
            )

    return jsonify({
        "message": "Problem submitted",
        "problem_id": problem_id
    }), 201

@problems_bp.get("")
def list_problems():
    with get_db() as db:
        rows = db.execute("SELECT * FROM problems ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])

@problems_bp.get("/<int:problem_id>")
def get_problem(problem_id):
    with get_db() as db:
        p = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not p:
            return jsonify({"error": "not found"}), 404
        result = dict(p)
        result["skills"] = json.loads(result.get("skills_json") or "[]")
        e = db.execute("SELECT * FROM evidence WHERE problem_id=?", (problem_id,)).fetchall()
        result["evidence"] = [dict(x) for x in e]
        return jsonify(result)

@problems_bp.post("/<int:problem_id>/analyze")
def analyze(problem_id):
    try:
        result = analyze_problem(problem_id)
        if result is None:
            return jsonify({"error": "not found"}), 404

        # Auto-assign top university after successful analysis
        try:
            auto_assignment = auto_assign_top_university(problem_id)
            if auto_assignment:
                result["auto_assignment"] = {
                    "university_id": auto_assignment.get("university_id"),
                    "university": auto_assignment.get("university"),
                    "rank": auto_assignment.get("rank"),
                    "final_score": auto_assignment.get("final_score"),
                }
        except Exception as assign_exc:
            current_app.logger.warning(
                "Auto-assignment failed for problem %s: %s", problem_id, assign_exc
            )
            result["auto_assignment_error"] = str(assign_exc)

        return jsonify(result)
    except Exception as exc:
        current_app.logger.exception("AI analysis failed")
        return jsonify({
            "error": "AI analysis failed",
            "detail": str(exc)
        }), 500

@problems_bp.post("/<int:problem_id>/verify-resolution")
def verify_resolution(problem_id):
    """Citizen verification endpoint: confirm problem is resolved with rating."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    is_resolved = data.get("is_resolved")
    if user_id is None or is_resolved is None:
        return jsonify({"error": "user_id and is_resolved required"}), 400

    with get_db() as db:
        # Verify problem exists
        p = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not p:
            return jsonify({"error": "problem not found"}), 404

        # Record feedback
        cur = db.execute("""
            INSERT INTO resolution_feedback (problem_id, user_id, is_resolved, rating, feedback_text, photo_evidence_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            problem_id,
            user_id,
            1 if is_resolved else 0,
            data.get("rating"),
            data.get("feedback_text"),
            data.get("photo_evidence_url")
        ))
        feedback_id = cur.lastrowid

    # Update problem status to completed if citizen verifies
    if is_resolved:
        with get_db() as db:
            db.execute("UPDATE problems SET status='completed' WHERE id=?", (problem_id,))

    return jsonify({
        "message": "resolution verified",
        "feedback_id": feedback_id,
        "verified": bool(is_resolved)
    }), 201
def matches(problem_id):
    """Return ranked university matches for a problem.

    Reads from problem_university_matches (with rank column) when available,
    falling back to the legacy matches table for backward compatibility.
    """
    with get_db() as db:
        # Prefer the new table with explicit rank
        rows = db.execute("""
            SELECT m.*, u.name AS university, u.city
            FROM problem_university_matches m
            JOIN universities u ON u.id=m.university_id
            WHERE m.problem_id=? ORDER BY m.rank ASC
        """, (problem_id,)).fetchall()

        if not rows:
            # Fallback: legacy matches table (no rank column)
            rows = db.execute("""
                SELECT m.*, u.name AS university, u.city
                FROM matches m JOIN universities u ON u.id=m.university_id
                WHERE m.problem_id=? ORDER BY m.final_score DESC
            """, (problem_id,)).fetchall()

        return jsonify([dict(r) for r in rows])
