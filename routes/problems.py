import os, uuid, json
from flask import Blueprint, request, jsonify, current_app, session
from auth.decorators import require_role
from werkzeug.utils import secure_filename
from database.db import get_db
from ai.pipeline import analyze_problem
from ai.classifier import classify_validity
from services.assignment_service import auto_assign_top_university

problems_bp = Blueprint("problems", __name__, url_prefix="/api/problems")

@problems_bp.post("")
@require_role('citizen', 'university', 'industry', 'admin')
def create_problem():
    # Support both multipart/form-data (with file uploads) and JSON bodies.
    payload = request.get_json(silent=True) or {}
    title = request.form.get("title") or payload.get("title")
    description = request.form.get("description") or payload.get("description")
    address = request.form.get("address") or payload.get("address")
    latitude = request.form.get("latitude") or payload.get("latitude")
    longitude = request.form.get("longitude") or payload.get("longitude")

    if not title or not description:
        return jsonify({"error": "title and description are required"}), 400

    # Run validity / spam detection BEFORE persisting the report
    validity = classify_validity(title, description or "")
    if validity["label"] == "INVALID":
        return jsonify({
            "error": "invalid_report",
            "label": validity["label"],
            "confidence": validity["confidence"],
            "message": validity["message"],
            "needs_review_reason": validity.get("needs_review_reason"),
        }), 400
    if validity["label"] == "NEEDS_REVIEW":
        return jsonify({
            "error": "needs_review",
            "label": validity["label"],
            "confidence": validity["confidence"],
            "message": validity["message"],
            "needs_review_reason": validity.get("needs_review_reason"),
            "quality_signals": validity.get("quality_signals"),
        }), 422

    user = session.get('user') or {}
    try:
        with get_db() as db:
            cur = db.execute("""
                INSERT INTO problems(title,description,address,latitude,longitude,created_by)
                VALUES(?,?,?,?,?,?)
            """, (title, description, (address or "").strip() or None,
                  float(latitude) if latitude not in (None, "", "None") else None,
                  float(longitude) if longitude not in (None, "", "None") else None,
                  user.get('id')))
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
    except Exception as exc:
        current_app.logger.exception("Failed to create problem")
        return jsonify({"error": "Failed to submit problem", "detail": str(exc)}), 500

    return jsonify({
        "message": "Problem submitted",
        "problem_id": problem_id,
        "validity": validity,
    }), 201

@problems_bp.get("")
@require_role('citizen', 'university', 'industry', 'admin')
def list_problems():
    user = session.get('user')
    with get_db() as db:
        if user and user.get('role') != 'admin':
            rows = db.execute("SELECT * FROM problems WHERE created_by=? ORDER BY id DESC", (user.get('id'),)).fetchall()
        else:
            rows = db.execute("SELECT * FROM problems ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])

@problems_bp.get("/<int:problem_id>")
@require_role('citizen', 'university', 'industry', 'admin')
def get_problem(problem_id):
    with get_db() as db:
        p = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not p:
            return jsonify({"error": "not found"}), 404
        user = session.get('user') or {}
        if user.get('role') != 'admin' and p['created_by'] not in (None, user.get('id')) and user.get('role') != 'university':
            return jsonify({"error": "not authorized"}), 403
        result = dict(p)
        result["skills"] = json.loads(result.get("skills_json") or "[]")
        e = db.execute("SELECT * FROM evidence WHERE problem_id=?", (problem_id,)).fetchall()
        result["evidence"] = [dict(x) for x in e]
        matches = db.execute("SELECT m.*, u.name AS university, u.city FROM problem_university_matches m JOIN universities u ON u.id=m.university_id WHERE m.problem_id=? ORDER BY m.rank ASC", (problem_id,)).fetchall()
        result["matches"] = [dict(x) for x in matches]
        assignments = db.execute("SELECT a.*, u.name AS university FROM assignments a LEFT JOIN universities u ON u.id=a.assignee_id WHERE a.problem_id=? ORDER BY a.id ASC", (problem_id,)).fetchall()
        result["assignments"] = [dict(x) for x in assignments]
        return jsonify(result)

@problems_bp.post("/<int:problem_id>/analyze")
@require_role('citizen', 'university', 'industry', 'admin')
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
@require_role('citizen', 'university', 'industry', 'admin')
def verify_resolution(problem_id):
    """Citizen verification endpoint: confirm problem is resolved with rating."""
    data = request.get_json() or {}
    user = session.get('user') or {}
    user_id = user.get('id')
    is_resolved = data.get("is_resolved")
    if user_id is None or is_resolved is None:
        return jsonify({"error": "is_resolved required"}), 400

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


@problems_bp.get("/<int:problem_id>/matches")
@require_role('citizen', 'university', 'industry', 'admin')
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
