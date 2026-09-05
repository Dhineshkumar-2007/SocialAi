import json
from flask import Blueprint, request, jsonify
from database.db import get_db
from auth.decorators import require_role

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")

@projects_bp.post("")
@require_role('university', 'industry', 'admin')
def create_project():
    data = request.get_json() or {}
    if not data.get("problem_id") or not data.get("name"):
        return jsonify({"error": "problem_id and name are required"}), 400

    milestones = data.get("milestones", [
        {"name": "Team formation", "status": "pending"},
        {"name": "Prototype", "status": "pending"},
        {"name": "Pilot", "status": "pending"},
        {"name": "Impact measurement", "status": "pending"}
    ])

    with get_db() as db:
        cur = db.execute("""
            INSERT INTO projects(problem_id,name,milestones_json)
            VALUES(?,?,?)
        """, (data["problem_id"], data["name"], json.dumps(milestones)))
        pid = cur.lastrowid

    return jsonify({"message": "project created", "id": pid}), 201

@projects_bp.get("/<int:project_id>/milestones")
@require_role('university', 'industry', 'admin', 'citizen')
def get_project_milestones(project_id):
    """Retrieve milestone progress for a workspace project."""
    with get_db() as db:
        # Check project exists
        proj = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return jsonify({"error": "Project not found"}), 404
        rows = db.execute(
            "SELECT * FROM project_milestones WHERE project_id=? ORDER BY created_at ASC",
            (project_id,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])


@projects_bp.post("/<int:project_id>/milestones")
@require_role('university', 'industry', 'admin')
def create_project_milestone(project_id):
    """Add a milestone to the execution workspace."""
    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400

    with get_db() as db:
        proj = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return jsonify({"error": "Project not found"}), 404
        cur = db.execute("""
            INSERT INTO project_milestones (project_id, title, description, stage, status, target_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            title,
            data.get("description"),
            data.get("stage", "prototype"),
            data.get("status", "pending"),
            data.get("target_date")
        ))
        milestone_id = cur.lastrowid
        row = db.execute("SELECT * FROM project_milestones WHERE id=?", (milestone_id,)).fetchone()
    return jsonify({"message": "milestone created", "milestone": dict(row)}), 201


@projects_bp.patch("/milestones/<int:milestone_id>")
@require_role('university', 'industry', 'admin')
def update_project_milestone(milestone_id):
    """Update milestone status, attach evidence, complete stage."""
    data = request.get_json() or {}
    updates = []
    values = []
    if "status" in data:
        updates.append("status = ?")
        values.append(data["status"])
    if "stage" in data:
        updates.append("stage = ?")
        values.append(data["stage"])
    if "evidence_url" in data:
        updates.append("evidence_url = ?")
        values.append(data["evidence_url"])
    if "description" in data:
        updates.append("description = ?")
        values.append(data["description"])
    if "completed_at" in data:
        updates.append("completed_at = ?")
        values.append(data["completed_at"])
    if not updates:
        return jsonify({"error": "nothing to update"}), 400

    values.append(milestone_id)
    with get_db() as db:
        db.execute(
            f"UPDATE project_milestones SET {', '.join(updates)} WHERE id=?",
            values
        )
    return jsonify({"message": "milestone updated"})


@projects_bp.post("/milestones/<int:milestone_id>/submit")
@require_role('university', 'industry', 'admin')
def submit_milestone_evidence(milestone_id):
    """Submit deliverable evidence for a milestone and mark as submitted."""
    data = request.get_json() or {}
    evidence_url = data.get("evidence_url")
    if not evidence_url:
        return jsonify({"error": "evidence_url required"}), 400

    with get_db() as db:
        db.execute(
            "UPDATE project_milestones SET status='submitted', evidence_url=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (evidence_url, milestone_id)
        )
    return jsonify({"message": "evidence submitted"})


@projects_bp.get("")
@require_role('university', 'industry', 'admin')
def list_projects():
    with get_db() as db:
        rows = db.execute("""
            SELECT p.*, pr.title AS problem_title
            FROM projects p JOIN problems pr ON pr.id=p.problem_id
            ORDER BY p.id DESC
        """).fetchall()
        result = []
        for r in rows:
            x = dict(r)
            x["milestones"] = json.loads(x["milestones_json"] or "[]")
            x["impact"] = json.loads(x["impact_json"] or "{}")
            result.append(x)
        return jsonify(result)

@projects_bp.patch("/<int:project_id>")
@require_role('university', 'industry', 'admin')
def update_project(project_id):
    data = request.get_json() or {}
    fields, values = [], []
    for key in ("status", "progress"):
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if "milestones" in data:
        fields.append("milestones_json=?")
        values.append(json.dumps(data["milestones"]))
    if "impact" in data:
        fields.append("impact_json=?")
        values.append(json.dumps(data["impact"]))

    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.append(project_id)
    with get_db() as db:
        db.execute(
            f"UPDATE projects SET {', '.join(fields)} WHERE id=?",
            values
        )
    return jsonify({"message": "updated"})


# ---------------------------------------------------------------------------
# Faculty / Student Assignment Endpoints (Phase 2 — Step 6)
# ---------------------------------------------------------------------------

@projects_bp.post("/<int:project_id>/assign")
@require_role('university', 'admin')
def assign_team_member(project_id):
    """Assign a faculty or student to a project.
    Body: {assignee_type: 'faculty'|'student', assignee_id: int, role?: str}
    """
    data = request.get_json() or {}
    assignee_type = data.get("assignee_type")
    assignee_id = data.get("assignee_id")
    role = data.get("role", "member")

    if assignee_type not in ("faculty", "student", "industry"):
        return jsonify({"error": "assignee_type must be 'faculty', 'student', or 'industry'"}), 400
    if assignee_id is None:
        return jsonify({"error": "assignee_id is required"}), 400

    with get_db() as db:
        proj = db.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return jsonify({"error": "Project not found"}), 404
        cur = db.execute("""
            INSERT INTO project_assignments(project_id, assignee_type, assignee_id, role)
            VALUES(?,?,?,?)
        """, (project_id, assignee_type, assignee_id, role))
        aid = cur.lastrowid
        row = db.execute("SELECT * FROM project_assignments WHERE id=?", (aid,)).fetchone()
    return jsonify({"message": "team member assigned", "assignment": dict(row)}), 201


@projects_bp.get("/<int:project_id>/assignments")
@require_role('university', 'admin')
def list_project_assignments(project_id):
    """List all faculty / student assignments for a project."""
    with get_db() as db:
        rows = db.execute("""
            SELECT pa.*, u.name AS assignee_name, u.email AS assignee_email
            FROM project_assignments pa
            LEFT JOIN users u ON u.id = pa.assignee_id
            WHERE pa.project_id=?
            ORDER BY pa.assigned_at DESC
        """, (project_id,)).fetchall()
    return jsonify({"count": len(rows), "assignments": [dict(r) for r in rows]})


@projects_bp.post("/milestones/<int:milestone_id>/verify")
@require_role('university', 'admin', 'citizen')
def verify_milestone(milestone_id):
    """Dual-citizen + faculty verification for a milestone.
    Body: {citizen_id?: int, faculty_id?: int, feedback_text?: str, is_confirmed: bool}
    """
    data = request.get_json() or {}
    if "is_confirmed" not in data:
        return jsonify({"error": "is_confirmed is required"}), 400

    with get_db() as db:
        ms = db.execute("SELECT id FROM project_milestones WHERE id=?", (milestone_id,)).fetchone()
        if not ms:
            return jsonify({"error": "Milestone not found"}), 404
        cur = db.execute("""
            INSERT INTO milestone_verifications(
                milestone_id, citizen_id, faculty_id, feedback_text, is_confirmed
            ) VALUES(?,?,?,?,?)
        """, (
            milestone_id,
            data.get("citizen_id"),
            data.get("faculty_id"),
            data.get("feedback_text"),
            1 if data.get("is_confirmed") else 0,
        ))
        vid = cur.lastrowid
        # If confirmed, mark milestone as verified
        if data.get("is_confirmed"):
            db.execute("UPDATE project_milestones SET status='verified' WHERE id=?", (milestone_id,))
        row = db.execute("SELECT * FROM milestone_verifications WHERE id=?", (vid,)).fetchone()
    return jsonify({"message": "verification recorded", "verification": dict(row)}), 201


@projects_bp.get("/<int:project_id>/impact")
@require_role('university', 'industry', 'admin', 'citizen')
def project_impact(project_id):
    """Aggregated impact metrics for a project (water saved, lives improved, etc.)."""
    with get_db() as db:
        proj = db.execute("SELECT id, name, impact_json FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return jsonify({"error": "Project not found"}), 404
        metrics = db.execute("""
            SELECT metric_key, metric_value, recorded_at
            FROM impact_metrics WHERE project_id=? ORDER BY recorded_at DESC
        """, (project_id,)).fetchall()
    return jsonify({
        "project_id": project_id,
        "project_name": proj["name"],
        "impact_json": json.loads(proj["impact_json"] or "{}"),
        "metrics": [dict(m) for m in metrics],
        "metric_count": len(metrics),
    })
