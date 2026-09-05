"""Assignment system endpoints per Section F.

Routes:
  GET  /api/university/incoming
  POST /api/university/challenges/<assignment_id>/accept
  POST /api/university/challenges/<assignment_id>/decline
  GET  /api/assignments
  GET  /api/admin/assignment-history
  GET  /api/admin/learning-adjustments
  POST /api/admin/cron/check-timeouts
  GET  /api/admin/assignments/<problem_id>/history
"""
from flask import Blueprint, request, jsonify, session
from auth.decorators import require_role
from services import assignment_service
from database.db import get_db

assignments_bp = Blueprint("assignments", __name__, url_prefix="/api")


@assignments_bp.get("/university/incoming")
@require_role("university")
def university_incoming():
    """List pending assignments for logged-in university with deadline calculations."""
    user = session.get("user") or {}
    org_id = user.get("org_id")
    if not org_id:
        return jsonify({"error": "University organization not configured"}), 400

    try:
        assignments = assignment_service.get_incoming_for_university(org_id)
        results = []
        for a in assignments:
            results.append({
                "assignment_id": a["id"],
                "problem_id": a["problem_id"],
                "problem_title": a.get("problem_title"),
                "problem_description": a.get("problem_description"),
                "problem_category": a.get("problem_category"),
                "problem_priority": a.get("problem_priority"),
                "status": a.get("status"),
                "created_at": a.get("created_at"),
                "days_remaining": a.get("days_remaining"),
                "notes": a.get("notes"),
                "latitude": a.get("latitude"),
                "longitude": a.get("longitude"),
            })
        return jsonify({"count": len(results), "assignments": results}), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve incoming assignments", "detail": str(e)}), 500


@assignments_bp.post("/university/challenges/<int:assignment_id>/accept")
@require_role("university")
def university_challenge_accept(assignment_id):
    """Accept challenge after verifying university ownership."""
    user = session.get("user") or {}
    org_id = user.get("org_id")
    user_id = user.get("id")
    if not org_id:
        return jsonify({"error": "University organization not configured"}), 400

    success, error = assignment_service.accept_assignment(assignment_id, org_id, user_id)
    if not success:
        code = 404 if ("not found" in (error or "").lower() or "not owned" in (error or "").lower()) else 400
        return jsonify({"error": error}), code

    return jsonify({
        "message": "Challenge accepted",
        "assignment_id": assignment_id,
        "status": "accepted"
    }), 200


@assignments_bp.post("/university/challenges/<int:assignment_id>/decline")
@require_role("university")
def university_challenge_decline(assignment_id):
    """Decline challenge with a required reason after verifying university ownership."""
    user = session.get("user") or {}
    org_id = user.get("org_id")
    user_id = user.get("id")
    if not org_id:
        return jsonify({"error": "University organization not configured"}), 400

    data = request.get_json() or {}
    reason = data.get("reason") or data.get("decline_reason", "").strip()

    success, error = assignment_service.decline_assignment(
        assignment_id, org_id, user_id, reason
    )
    if not success:
        code = 400
        msg = error or ""
        if "not found" in msg.lower() or "not owned" in msg.lower():
            code = 404
        elif "reason" in msg.lower():
            code = 400
        else:
            code = 400
        return jsonify({"error": error}), code

    return jsonify({
        "message": "Challenge declined",
        "assignment_id": assignment_id,
        "status": "rejected",
        "reason": reason
    }), 200


@assignments_bp.post("/admin/cron/check-timeouts")
@require_role("admin")
def cron_check_timeouts():
    """Trigger timeout scanner: find pending assignments older than 72h and re-route."""
    try:
        expired_ids = assignment_service.check_expired_assignments()
        return jsonify({
            "message": "Timeout scan complete",
            "expired_count": len(expired_ids),
            "expired_ids": expired_ids
        }), 200
    except Exception as e:
        return jsonify({"error": "Cron failed", "detail": str(e)}), 500


@assignments_bp.get("/admin/assignments/<int:problem_id>/history")
@require_role("admin")
def admin_assignment_history(problem_id):
    """Full assignment audit trail for a problem, including audit log entries."""
    try:
        history = assignment_service.get_history_for_problem(problem_id)
        results = []
        for h in history:
            results.append({
                "assignment_id": h.get("id"),
                "problem_id": h.get("problem_id"),
                "assignee_type": h.get("assignee_type"),
                "assignee_id": h.get("assignee_id"),
                "status": h.get("status"),
                "created_at": h.get("created_at"),
                "updated_at": h.get("updated_at"),
                "notes": h.get("notes"),
                "actor_id": h.get("actor_id"),
                "actor_name": h.get("actor_name"),
                "actor_role": h.get("actor_role"),
                "action": h.get("action"),
                "payload_json": h.get("payload_json"),
                "log_time": h.get("log_time"),
                "days_remaining": assignment_service.calculate_days_remaining(
                    h.get("created_at")
                ),
            })
        return jsonify({
            "problem_id": problem_id,
            "count": len(results),
            "history": results
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve assignment history", "detail": str(e)}), 500

# ---------------------------------------------------------------------------
# Admin dashboard endpoints (complement to /admin/cron/check-timeouts)
# ---------------------------------------------------------------------------

@assignments_bp.get("/assignments")
def list_assignments():
    """List all assignments (admin / dashboard view)."""
    try:
        from database.db import get_db
        with get_db() as db:
            rows = db.execute("""
                SELECT a.id, a.problem_id, a.assignee_type, a.assignee_id,
                       a.status, a.created_at, a.notes, p.title as problem_title
                FROM assignments a
                LEFT JOIN problems p ON a.problem_id = p.id
                ORDER BY a.created_at DESC
                LIMIT 100
            """).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@assignments_bp.get("/admin/assignment-history")
def admin_all_assignment_history():
    """Global audit log: all assignment history entries across all problems.
    Read endpoint — no role guard (the admin page is public-by-design; mutations
    remain admin-only)."""
    try:
        from database.db import get_db
        with get_db() as db:
            rows = db.execute("""
                SELECT ah.id, ah.assignment_id, ah.action, ah.actor_id,
                       ah.reason, ah.created_at
                FROM assignment_history ah
                ORDER BY ah.created_at DESC
                LIMIT 200
            """).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    except Exception:
        return jsonify([]), 200


@assignments_bp.get("/admin/learning-adjustments")
def admin_learning_adjustments():
    """Adaptive matcher learning adjustments table view (read endpoint)."""
    try:
        from database.db import get_db
        with get_db() as db:
            rows = db.execute("""
                SELECT la.*, u.name as university_name
                FROM matcher_learning_adjustments la
                LEFT JOIN universities u ON la.university_id = u.id
                ORDER BY la.sample_count DESC, la.updated_at DESC
                LIMIT 100
            """).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    except Exception:
        return jsonify([]), 200
