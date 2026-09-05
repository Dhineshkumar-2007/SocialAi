import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from database.db import get_db
from services.assignment_service import check_expired_assignments
from auth.decorators import require_role

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/audit")
@require_role('admin')
def audit_trail():
    with get_db() as db:
        rows = db.execute("""
            SELECT
                p.id AS problem_id,
                p.title,
                p.status,
                u.name AS actor_name,
                u.role AS actor_role,
                p.created_at AS time,
                'submitted' AS action
            FROM problems p
            LEFT JOIN users u ON u.id = p.created_by
            ORDER BY p.created_at DESC LIMIT 20
        """).fetchall()
    return jsonify({"logs": [{"time": r["time"], "action": r["action"], "actor": (r["actor_name"] or "System") + (f" ({r["actor_role"]})" if r.get("actor_role") else ""), "target": f"#{r['problem_id']}", "status": "success"} for r in map(dict, rows)]})


@admin_bp.get("/assignment-history")
@require_role('admin')
def assignment_history():
    """Return audit trail of assignment lifecycle events (accepts, declines, timeouts, re-routes)."""
    with get_db() as db:
        rows = db.execute("""
            SELECT
                ah.id,
                ah.assignment_id,
                ah.action,
                ah.reason,
                ah.created_at,
                a.problem_id,
                a.assignee_id,
                u.name AS university_name
            FROM assignment_history ah
            JOIN assignments a ON a.id = ah.assignment_id
            LEFT JOIN universities u ON u.id = a.assignee_id AND a.assignee_type='university'
            ORDER BY ah.created_at DESC
            LIMIT 100
        """).fetchall()
        return jsonify([dict(r) for r in rows])


@admin_bp.get("/learning-adjustments")
@require_role('admin')
def learning_adjustments():
    """Return adaptive matcher penalty factors learned from decline patterns."""
    try:
        with get_db() as db:
            rows = db.execute("""
                SELECT
                    la.university_id,
                    u.name AS university_name,
                    la.category,
                    la.penalty_factor,
                    la.sample_count,
                    la.last_reason,
                    la.updated_at
                FROM matcher_learning_adjustments la
                LEFT JOIN universities u ON u.id = la.university_id
                ORDER BY la.updated_at DESC
            """).fetchall()
            return jsonify([dict(r) for r in rows])
    except Exception as exc:
        return jsonify({"error": "Failed to load learning adjustments", "detail": str(exc)}), 500


@admin_bp.post("/cron/check-timeouts")
@require_role('admin')
def trigger_timeout_scan():
    """Manually trigger timeout scanner to process assignments pending beyond 72h."""
    try:
        expired_ids = check_expired_assignments()
        return jsonify({
            "message": f"Timeout scan completed. {len(expired_ids)} expired assignment(s) processed.",
            "expired_ids": expired_ids
        })
    except Exception as exc:
        return jsonify({
            "error": "Timeout scan failed",
            "detail": str(exc)
        }), 500


@admin_bp.get("/universities/pending")
@require_role('admin')
def list_pending_universities():
    """Return universities awaiting admin verification."""
    with get_db() as db:
        rows = db.execute("""
            SELECT id, name, city, state, contact_email, website,
                   accreditation, created_at
            FROM universities
            WHERE verified = 0
            ORDER BY created_at DESC NULLS LAST, id DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])


@admin_bp.post("/universities/<int:uid>/verify")
@require_role('admin')
def verify_university(uid):
    """Approve a pending university registration."""
    with get_db() as db:
        row = db.execute("SELECT id, name, verified FROM universities WHERE id=?", (uid,)).fetchone()
        if not row:
            return jsonify({"error": "University not found"}), 404
        if row["verified"]:
            return jsonify({"message": f"{row['name']} already verified", "id": uid}), 200
        db.execute("UPDATE universities SET verified = 1 WHERE id=?", (uid,))
        # Log the verification event (uses assignment_history as a generic audit table)
        try:
            db.execute("""
                INSERT INTO assignment_history(assignment_id, action, reason, created_at)
                VALUES (0, 'university_verified', ?, CURRENT_TIMESTAMP)
            """, (f"university_id={uid} name={row['name']}",))
        except Exception:
            pass  # audit log is best-effort
        return jsonify({"message": f"{row['name']} verified", "id": uid}), 200


@admin_bp.post("/universities/<int:uid>/reject")
@require_role('admin')
def reject_university(uid):
    """Reject a pending university registration."""
    reason = (request.get_json(silent=True) or {}).get("reason", "")
    with get_db() as db:
        row = db.execute("SELECT id, name FROM universities WHERE id=?", (uid,)).fetchone()
        if not row:
            return jsonify({"error": "University not found"}), 404
        # Mark unverified; keeps the record for audit (do not delete)
        try:
            db.execute("""
                INSERT INTO assignment_history(assignment_id, action, reason, created_at)
                VALUES (0, 'university_rejected', ?, CURRENT_TIMESTAMP)
            """, (f"university_id={uid} name={row['name']} reason={reason}",))
        except Exception:
            pass
        return jsonify({"message": f"{row['name']} rejected", "id": uid}), 200


@admin_bp.get("/stats")
@require_role('admin')
def admin_stats():
    """Dashboard overview statistics."""
    with get_db() as db:
        total_problems = db.execute("SELECT COUNT(*) as c FROM problems").fetchone()["c"]
        active_problems = db.execute("""
            SELECT COUNT(*) as c FROM problems
            WHERE status IN ('pending', 'assigned', 'in_progress', 'analyzed')
        """).fetchone()["c"]
        pending_assignments = db.execute("""
            SELECT COUNT(*) as c FROM assignments WHERE status='pending'
        """).fetchone()["c"]
        total_adjustments = db.execute("SELECT COUNT(*) as c FROM matcher_learning_adjustments").fetchone()["c"]

        # Matcher accuracy: percentage of accepted vs total assignments
        accepted = db.execute("""
            SELECT COUNT(*) as c FROM assignments WHERE status='accepted'
        """).fetchone()["c"]
        total_assignments = db.execute("SELECT COUNT(*) as c FROM assignments").fetchone()["c"]
        accuracy = round((accepted / total_assignments * 100), 1) if total_assignments > 0 else 0.0

        return jsonify({
            "total_problems": total_problems,
            "active_problems": active_problems,
            "pending_assignments": pending_assignments,
            "total_adjustments": total_adjustments,
            "matcher_accuracy": accuracy
        })
