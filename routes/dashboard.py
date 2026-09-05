"""Dashboard data routes."""
from flask import Blueprint, jsonify, render_template
from database.db import get_db
from auth.decorators import require_role

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/public")
def public_metrics():
    """Public dashboard metrics."""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        by_status = db.execute(
            "SELECT status, COUNT(*) as count FROM problems GROUP BY status"
        ).fetchall()
        by_category = db.execute(
            "SELECT category, COUNT(*) as count FROM problems WHERE category IS NOT NULL GROUP BY category"
        ).fetchall()
        high_priority = db.execute(
            "SELECT COUNT(*) FROM problems WHERE priority_level IN ('critical','high')"
        ).fetchone()[0]
        active_projects = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status='in_progress'"
        ).fetchone()[0]
        completed_projects = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status='completed'"
        ).fetchone()[0]
        total_matches = db.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        total_assignments = db.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
        universities = db.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
        industry_partners = db.execute("SELECT COUNT(*) FROM industry_partners").fetchone()[0]

        return jsonify({
            "total_problems": total,
            "problems_by_status": {r["status"]: r["count"] for r in by_status},
            "problems_by_category": {r["category"]: r["count"] for r in by_category},
            "high_priority_count": high_priority,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "total_matches": total_matches,
            "total_assignments": total_assignments,
            "universities": universities,
            "industry_partners": industry_partners,
        })


@dashboard_bp.get("/admin")
@require_role('admin', 'superadmin')
def admin_metrics():
    """Admin dashboard metrics — full system view."""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        pending = db.execute(
            "SELECT COUNT(*) FROM problems WHERE status='submitted'"
        ).fetchone()[0]
        analyzed = db.execute(
            "SELECT COUNT(*) FROM problems WHERE status='analyzed'"
        ).fetchone()[0]
        high_priority = db.execute(
            "SELECT COUNT(*) FROM problems WHERE priority_level IN ('critical','high')"
        ).fetchone()[0]
        duplicates = db.execute(
            "SELECT COUNT(*) FROM problem_links"
        ).fetchone()[0]
        assigned = db.execute(
            "SELECT COUNT(*) FROM assignments WHERE status='pending'"
        ).fetchone()[0]
        in_progress = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status IN ('proposed','approved','in_progress')"
        ).fetchone()[0]
        field_testing = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status='field_testing'"
        ).fetchone()[0]
        deployed = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status='deployed'"
        ).fetchone()[0]
        completed = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status='completed'"
        ).fetchone()[0]
        verified_universities = db.execute(
            "SELECT COUNT(*) FROM universities WHERE verified=1"
        ).fetchone()[0]
        total_assignments = db.execute(
            "SELECT COUNT(*) FROM assignments"
        ).fetchone()[0]
        total_projects = db.execute(
            "SELECT COUNT(*) FROM projects"
        ).fetchone()[0]
        milestones = db.execute(
            "SELECT COUNT(*) FROM project_milestones"
        ).fetchone()[0]
        milestone_verified = db.execute(
            "SELECT COUNT(*) FROM project_milestones WHERE status='verified'"
        ).fetchone()[0]
        milestone_pending = db.execute(
            "SELECT COUNT(*) FROM project_milestones WHERE status='pending'"
        ).fetchone()[0]
        impact_records = db.execute(
            "SELECT COUNT(*) FROM impact_metrics"
        ).fetchone()[0]
        project_assignments = db.execute(
            "SELECT COUNT(*) FROM project_assignments"
        ).fetchone()[0]
        timeout_count = db.execute(
            "SELECT COUNT(*) FROM assignment_history WHERE action='expired'"
        ).fetchone()[0]
        declination_count = db.execute(
            "SELECT COUNT(*) FROM assignment_history WHERE action LIKE 'response_rejected%'"
        ).fetchone()[0]

        # Problems by category (top 5)
        by_category = db.execute("""
            SELECT category, COUNT(*) as count
            FROM problems WHERE category IS NOT NULL
            GROUP BY category ORDER BY count DESC LIMIT 5
        """).fetchall()

        # Projects by status (full lifecycle)
        project_status_breakdown = db.execute("""
            SELECT status, COUNT(*) as count FROM projects GROUP BY status
        """).fetchall()

        # Recent problems
        recent = db.execute(
            "SELECT id, title, category, priority_level, status, created_at "
            "FROM problems ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        # Learning adjustments (adaptive penalty table)
        learning = db.execute("""
            SELECT la.*, u.name as university_name
            FROM matcher_learning_adjustments la
            LEFT JOIN universities u ON la.university_id = u.id
            ORDER BY la.sample_count DESC LIMIT 5
        """).fetchall()

        return jsonify({
            "total_problems": total,
            "pending_ai_analysis": pending,
            "analyzed": analyzed,
            "high_priority": high_priority,
            "duplicate_links": duplicates,
            "pending_assignments": assigned,
            "active_projects": in_progress,
            "field_testing_projects": field_testing,
            "deployed_projects": deployed,
            "completed_projects": completed,
            "total_projects": total_projects,
            "total_assignments": total_assignments,
            "milestones": milestones,
            "milestone_verified": milestone_verified,
            "milestone_pending": milestone_pending,
            "impact_records": impact_records,
            "project_team_assignments": project_assignments,
            "verified_universities": verified_universities,
            "timeout_count": timeout_count,
            "declination_count": declination_count,
            "problems_by_category": [{"category": r["category"], "count": r["count"]} for r in by_category],
            "project_status_breakdown": [{"status": r["status"], "count": r["count"]} for r in project_status_breakdown],
            "recent_problems": [dict(r) for r in recent],
            "learning_adjustments": [dict(r) for r in learning],
        })


@dashboard_bp.get("/university/<int:university_id>")
@require_role('university', 'admin')
def university_metrics(university_id):
    """University dashboard metrics."""
    with get_db() as db:
        assignments = db.execute(
            "SELECT COUNT(*) FROM assignments WHERE assignee_type='university' AND assignee_id=?",
            (university_id,)
        ).fetchone()[0]
        in_progress = db.execute(
            "SELECT COUNT(*) FROM projects WHERE assigned_to_type='university' AND assigned_to_id=? AND status='in_progress'",
            (university_id,)
        ).fetchone()[0]
        completed = db.execute(
            "SELECT COUNT(*) FROM projects WHERE assigned_to_type='university' AND assigned_to_id=? AND status='completed'",
            (university_id,)
        ).fetchone()[0]
        return jsonify({
            "total_assignments": assignments,
            "in_progress_projects": in_progress,
            "completed_projects": completed,
        })


@dashboard_bp.get("/industry/<int:industry_id>")
@require_role('industry', 'admin')
def industry_metrics(industry_id):
    """Industry dashboard metrics."""
    with get_db() as db:
        assignments = db.execute(
            "SELECT COUNT(*) FROM assignments WHERE assignee_type='industry' AND assignee_id=?",
            (industry_id,)
        ).fetchone()[0]
        return jsonify({
            "total_assignments": assignments,
        })


# ── Public-facing pages (/explore, /explore/solutions, /institutions, /impact) ─

public_bp = Blueprint("public", __name__)


@public_bp.get("/explore")
def explore_problems_page():
    """Public list of all reported problems (sanitized — no PII)."""
    return render_template("public/explore_problems.html")


@public_bp.get("/explore/solutions")
def explore_solutions_page():
    """Public list of completed/in-progress projects (verified solutions)."""
    return render_template("public/explore_solutions.html")


@public_bp.get("/institutions")
def institutions_page():
    """Public directory of verified universities + industry partners."""
    return render_template("public/institutions.html")


@public_bp.get("/impact")
def impact_page():
    """Public impact dashboard — aggregate stats only."""
    return render_template("public/impact.html")


# ── Data endpoints consumed by the public pages ───────────────────────────

@public_bp.get("/api/explore/problems")
def api_explore_problems():
    """Public list of problems (anonymized, no reporter info)."""
    with get_db() as db:
        rows = db.execute("""
            SELECT id, title, description, category, priority_level, status,
                   address, created_at
            FROM problems
            WHERE status IN ('submitted','analyzed','assigned','in_progress','completed')
            ORDER BY created_at DESC
            LIMIT 100
        """).fetchall()
        return jsonify([dict(r) for r in rows])


@public_bp.get("/api/explore/solutions")
def api_explore_solutions():
    """Public list of completed/in-progress projects."""
    with get_db() as db:
        rows = db.execute("""
            SELECT pr.id, pr.problem_id, pr.name, pr.status, pr.progress, pr.started_at, pr.completed_at,
                   p.title AS problem_title, p.category,
                   u.name AS institution_name
            FROM projects pr
            JOIN problems p ON p.id = pr.problem_id
            LEFT JOIN universities u
                ON u.id = pr.assigned_to_id AND pr.assigned_to_type = 'university'
            WHERE pr.status IN ('in_progress','completed','deployed')
            ORDER BY pr.started_at DESC
            LIMIT 60
        """).fetchall()
        return jsonify([dict(r) for r in rows])


@public_bp.get("/api/institutions")
def api_institutions():
    """Public directory of verified universities + industry partners."""
    with get_db() as db:
        unis = db.execute("""
            SELECT id, name, type, district, state, verified, capacity
            FROM universities
            WHERE verified = 1
            ORDER BY name
        """).fetchall()
        industries = db.execute("""
            SELECT id, name, sector, district, state
            FROM industry_partners
            ORDER BY name
        """).fetchall()
        return jsonify({
            "universities": [dict(u) for u in unis],
            "industry_partners": [dict(i) for i in industries],
        })


@public_bp.get("/api/impact")
def api_impact():
    """Public impact metrics — aggregate, no PII."""
    with get_db() as db:
        total_problems = db.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        completed_problems = db.execute(
            "SELECT COUNT(*) FROM problems WHERE status='completed'"
        ).fetchone()[0]
        in_progress = db.execute(
            "SELECT COUNT(*) FROM problems WHERE status IN ('assigned','in_progress')"
        ).fetchone()[0]
        verified_unis = db.execute(
            "SELECT COUNT(*) FROM universities WHERE verified=1"
        ).fetchone()[0]
        completed_projects = db.execute(
            "SELECT COUNT(*) FROM projects WHERE status IN ('completed','deployed')"
        ).fetchone()[0]

        by_category = db.execute("""
            SELECT category, COUNT(*) AS count
            FROM problems
            WHERE category IS NOT NULL
            GROUP BY category ORDER BY count DESC
        """).fetchall()

        # Estimated people impacted (rough heuristic: 50 per solved problem,
        # matched to current scale; replaced with real survey data later).
        people_impacted = completed_problems * 50

        return jsonify({
            "total_problems": total_problems,
            "completed_problems": completed_problems,
            "in_progress_problems": in_progress,
            "people_impacted": people_impacted,
            "verified_universities": verified_unis,
            "completed_projects": completed_projects,
            "problems_by_category": [
                {"category": r["category"], "count": r["count"]}
                for r in by_category
            ],
        })
