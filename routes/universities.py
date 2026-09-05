from flask import Blueprint, request, jsonify, session
from database.db import get_db

universities_bp = Blueprint("universities", __name__, url_prefix="/api/universities")

def _get_user():
    return session.get('user') or {}

def _uid(user):
    """University institution_id from session user — prefers org_id (auth model field)."""
    return user.get('org_id') or user.get('institution_id') or user.get('id')


# ── Internal data helpers ────────────────────────────────────────────────────

def _university_row(db, uid):
    """Load one university with all its nested profiles."""
    u = db.execute("SELECT * FROM universities WHERE id=?", (uid,)).fetchone()
    if not u:
        return None
    row = dict(u)
    row["faculty"] = [
        dict(r) for r in
        db.execute("SELECT * FROM faculty WHERE university_id=?", (uid,)).fetchall()
    ]
    row["labs"] = [
        dict(r) for r in
        db.execute("SELECT * FROM labs WHERE university_id=?", (uid,)).fetchall()
    ]
    row["projects"] = [
        dict(r) for r in
        db.execute("SELECT * FROM previous_projects WHERE university_id=?", (uid,)).fetchall()
    ]
    row["technologies"] = [
        dict(r) for r in
        db.execute("SELECT * FROM university_technologies WHERE university_id=?", (uid,)).fetchall()
    ]
    return row


def _problem_rows_for_university(db, uid, status_filter=None):
    """
    Problems assigned to this university via the assignments table.
    The assignments table uses: assignee_type='university', assignee_id=university_id.
    """
    query = """
        SELECT
            p.id, p.title, p.description, p.status,
            p.priority, p.category, p.address,
            p.created_at, p.assigned_at,
            a.id         AS assignment_id,
            a.status     AS assignment_status,
            COALESCE(
                (SELECT m.final_score FROM problem_university_matches m
                  WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                  ORDER BY m.rank LIMIT 1),
                (SELECT n.final_score FROM matches n
                  WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                  ORDER BY n.id LIMIT 1),
                0
            ) AS match_score,
            COALESCE(
                (SELECT m.explanation FROM problem_university_matches m
                  WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                  ORDER BY m.rank LIMIT 1),
                (SELECT n.explanation FROM matches n
                  WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                  ORDER BY n.id LIMIT 1),
                NULL
            ) AS match_reasons,
            a.declined_at,
            a.decline_reason,
            a.notes      AS assignment_notes,
            u.name       AS declined_by_name
        FROM assignments a
        JOIN problems p ON p.id = a.problem_id
        LEFT JOIN universities u ON u.id = a.declined_by
        WHERE a.assignee_type = 'university'
          AND a.assignee_id = ?
    """
    params = [uid]
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        query += f" AND a.status IN ({placeholders})"
        params += list(status_filter)
    query += " ORDER BY a.created_at DESC"
    return [dict(r) for r in db.execute(query, params).fetchall()]


# ── JSON API ────────────────────────────────────────────────────────────────

@universities_bp.get("")
def list_universities():
    """Public list of verified institutions for the HEI register dropdown
    and public directory. Read-only, no auth required."""
    with get_db() as db:
        rows = db.execute("""
            SELECT id, name, institution_type, city, state, verified, capacity
            FROM universities
            WHERE verified = 1
            ORDER BY name
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@universities_bp.get("/me")
def my_university():
    """Return the university profile for the currently logged-in institution user."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    with get_db() as db:
        u = _university_row(db, uid)
        if not u:
            return jsonify({"error": "university not found"}), 404
        for field in ("capacity", "total_capacity"):
            u.pop(field, None)
        return jsonify(u)


@universities_bp.get("/challenges")
def list_challenges():
    """Challenges (assignments) routed to the authenticated university."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    with get_db() as db:
        rows = _problem_rows_for_university(db, uid)
        for row in rows:
            row["evidence_count"] = db.execute(
                "SELECT COUNT(*) FROM evidence WHERE problem_id=?",
                (row["id"],)
            ).fetchone()[0]
        return jsonify(rows)


@universities_bp.get("/challenges/<int:assignment_id>")
def get_challenge(assignment_id):
    """Full challenge detail for the authenticated university."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    with get_db() as db:
        row = db.execute("""
            SELECT
                a.*,
                p.id           AS problem_id,
                p.title        AS problem_title,
                p.description  AS problem_description,
                p.category     AS problem_category,
                p.priority     AS problem_priority,
                p.status       AS problem_status,
                p.address      AS problem_address,
                p.created_at   AS problem_created_at,
                u.name         AS institution_name
            FROM assignments a
            JOIN problems p ON p.id = a.problem_id
            JOIN universities u ON u.id = a.assignee_id
            WHERE a.id = ? AND a.assignee_type = 'university' AND a.assignee_id = ?
        """, (assignment_id, uid)).fetchone()

        if not row:
            return jsonify({"error": "challenge not found"}), 404

        result = dict(row)

        # Evidence
        result["evidence"] = [
            dict(r) for r in
            db.execute(
                "SELECT id, filename, uploaded_at FROM evidence WHERE problem_id=?",
                (row["problem_id"],)
            ).fetchall()
        ]

        # Routing history: all assignment attempts for this problem
        result["routing_history"] = [
            dict(r) for r in
            db.execute("""
                SELECT a.id AS assignment_id, a.status,
                       COALESCE(
                           (SELECT m.final_score FROM problem_university_matches m
                            WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                            ORDER BY m.rank LIMIT 1),
                           (SELECT n.final_score FROM matches n
                            WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                            ORDER BY n.id LIMIT 1),
                           0) AS score,
                       COALESCE(
                           (SELECT m.explanation FROM problem_university_matches m
                            WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                            ORDER BY m.rank LIMIT 1),
                           (SELECT n.explanation FROM matches n
                            WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                            ORDER BY n.id LIMIT 1),
                           NULL) AS reasons,
                       a.declined_at, a.decline_reason, a.assigned_at,
                       u.name AS institution_name,
                       CASE a.status
                         WHEN 'assigned'  THEN 'Pending'
                         WHEN 'accepted'  THEN 'Accepted'
                         WHEN 'declined'  THEN 'Declined'
                         ELSE a.status
                       END AS status_label
                FROM assignments a
                JOIN universities u ON u.id = a.assignee_id
                WHERE a.problem_id = ?
                ORDER BY a.assigned_at ASC
            """, (row["problem_id"],)).fetchall()
        ]

        return jsonify(result)


@universities_bp.get("/projects")
def list_university_projects():
    """Active projects for the authenticated university."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    with get_db() as db:
        rows = db.execute("""
            SELECT
                pr.id,
                pr.title,
                pr.description,
                pr.status    AS project_status,
                pr.progress  AS project_progress,
                pr.created_at,
                pr.updated_at,
                p.id        AS problem_id,
                p.title     AS problem_title,
                p.category  AS problem_category,
                p.citizen_name,
                p.status    AS problem_status,
                a.id        AS assignment_id,
                COALESCE(
                    COALESCE(
                        (SELECT m.final_score FROM problem_university_matches m
                         WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                         ORDER BY m.rank LIMIT 1),
                        (SELECT n.final_score FROM matches n
                         WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                         ORDER BY n.id LIMIT 1)
                    ), 0
                ) AS match_score,
                COALESCE(
                    (SELECT m.explanation FROM problem_university_matches m
                     WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                     ORDER BY m.rank LIMIT 1),
                    (SELECT n.explanation FROM matches n
                     WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                     ORDER BY n.id LIMIT 1)
                ) AS match_reasons
            FROM assignments a
            JOIN projects pr ON pr.problem_id = a.problem_id AND pr.assigned_to_id = a.assignee_id
            JOIN problems p ON p.id = a.problem_id
            WHERE a.assignee_type = 'university' AND a.assignee_id = ?
            ORDER BY pr.updated_at DESC
        """, (uid,)).fetchall()
        return jsonify([dict(r) for r in rows])


@universities_bp.get("/stats")
def dashboard_stats():
    """6 metric tiles for the university dashboard."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    base = "FROM assignments WHERE assignee_type='university' AND assignee_id=?"
    with get_db() as db:
        total = db.execute(f"SELECT COUNT(*) {base}", (uid,)).fetchone()[0]
        # The platform's assignment statuses are pending/accepted/rejected/
        # in_progress/completed (CHECK constraint) — 'assigned' and
        # 'pending_review' are legacy UI names that never occur.
        assigned = db.execute(
            f"SELECT COUNT(*) {base} AND status IN ('assigned','pending')", (uid,)
        ).fetchone()[0]
        pending_review = db.execute(
            f"SELECT COUNT(*) {base} AND status IN ('assigned','pending')", (uid,)
        ).fetchone()[0]

        active = db.execute(f"""
            SELECT COUNT(*) FROM projects pr
            JOIN assignments a ON a.problem_id = pr.problem_id AND a.assignee_type='university'
            WHERE a.assignee_type='university' AND a.assignee_id=? AND pr.status='in_progress'
        """, (uid,)).fetchone()[0]

        completed = db.execute(f"""
            SELECT COUNT(*) FROM projects pr
            JOIN assignments a ON a.problem_id = pr.problem_id AND a.assignee_type='university'
            WHERE a.assignee_type='university' AND a.assignee_id=? AND pr.status='completed'
        """, (uid,)).fetchone()[0]

        awaiting_verification = db.execute(f"""
            SELECT COUNT(*) FROM projects pr
            JOIN assignments a ON a.problem_id = pr.problem_id AND a.assignee_type='university'
            WHERE a.assignee_type='university' AND a.assignee_id=? AND pr.status='awaiting_verification'
        """, (uid,)).fetchone()[0]

        denom = completed + active
        success_rate = round((completed / denom) * 100, 1) if denom > 0 else 0.0

        return jsonify({
            "total": total,
            "assigned": assigned,
            "pending_review": pending_review,
            "active": active,
            "completed": completed,
            "awaiting_verification": awaiting_verification,
            "success_rate": success_rate,
        })


@universities_bp.get("/projects/<int:project_id>")
def get_project(project_id):
    """Full project detail for the authenticated university."""
    user = _get_user()
    if user.get("role") not in ("university", "admin"):
        return jsonify({"error": "unauthorized"}), 403

    uid = _uid(user)
    with get_db() as db:
        row = db.execute("""
            SELECT pr.*,
                   a.institution_id,
                   p.title,
                   p.description,
                   p.category,
                   p.address,
                   p.citizen_name,
                   p.status    AS problem_status,
                   p.created_at AS problem_created_at
            FROM projects pr
            JOIN assignments a ON a.problem_id = pr.problem_id AND a.assignee_type='university'
            JOIN problems p ON p.id = a.problem_id
            WHERE pr.id = ? AND a.assignee_type = 'university' AND a.assignee_id = ?
        """, (project_id, uid)).fetchone()

        if not row:
            return jsonify({"error": "not found"}), 404

        result = dict(row)

        # Milestones
        result["milestones"] = [
            dict(r) for r in
            db.execute(
                "SELECT * FROM project_milestones WHERE project_id=? ORDER BY id",
                (project_id,)
            ).fetchall()
        ]

        # Institution evidence
        result["evidence"] = [
            dict(r) for r in
            db.execute(
                "SELECT * FROM project_evidence WHERE project_id=? ORDER BY uploaded_at DESC",
                (project_id,)
            ).fetchall()
        ]

        # Team members
        result["team"] = [
            dict(r) for r in
            db.execute(
                "SELECT pa.*, u.name AS assignee_name, u.email AS assignee_email "
                "FROM project_assignments pa "
                "LEFT JOIN users u ON u.id = pa.assignee_id "
                "WHERE pa.project_id=?",
                (project_id,)
            ).fetchall()
        ]

        # Problem evidence
        result["problem_evidence"] = [
            dict(r) for r in
            db.execute(
                "SELECT id, filename, uploaded_at FROM evidence WHERE problem_id=?",
                (row["problem_id"],)
            ).fetchall()
        ]

        # Routing history
        result["routing_history"] = [
            dict(r) for r in
            db.execute("""
                SELECT a.id AS assignment_id, a.status,
                       COALESCE(
                           (SELECT m.final_score FROM problem_university_matches m
                            WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                            ORDER BY m.rank LIMIT 1),
                           (SELECT n.final_score FROM matches n
                            WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                            ORDER BY n.id LIMIT 1),
                           0) AS score,
                       COALESCE(
                           (SELECT m.explanation FROM problem_university_matches m
                            WHERE m.problem_id = a.problem_id AND m.university_id = a.assignee_id
                            ORDER BY m.rank LIMIT 1),
                           (SELECT n.explanation FROM matches n
                            WHERE n.problem_id = a.problem_id AND n.university_id = a.assignee_id
                            ORDER BY n.id LIMIT 1),
                           NULL) AS reasons,
                       a.declined_at, a.decline_reason, a.assigned_at,
                       u.name AS institution_name,
                       CASE a.status
                         WHEN 'assigned'  THEN 'Pending'
                         WHEN 'accepted'  THEN 'Accepted'
                         WHEN 'declined'  THEN 'Declined'
                         ELSE a.status
                       END AS status_label
                FROM assignments a
                JOIN universities u ON u.id = a.assignee_id
                WHERE a.problem_id = ?
                ORDER BY a.assigned_at ASC
            """, (row["problem_id"],)).fetchall()
        ]

        return jsonify(result)
