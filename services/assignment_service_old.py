"""Assignment service layer - business logic for assignments."""
import json
from datetime import datetime, timedelta
from database.db import get_db, audit_log
from models.assignment import Assignment
from models.notification import Notification
from models.industry_partner import IndustryPartner

DEFAULT_DEADLINE_DAYS = 14


def get_incoming_for_university(org_id):
    """List pending assignments for a university, with problem details and days_remaining."""
    with get_db() as db:
        rows = db.execute(
            """SELECT a.*, p.title as problem_title, p.description as problem_description,
                      p.category as problem_category, p.priority_level as problem_priority,
                      p.latitude, p.longitude,
                      u.name as university_name
               FROM assignments a
               JOIN problems p ON p.id = a.problem_id
               JOIN universities u ON u.id = a.assignee_id
               WHERE a.assignee_type = 'university'
                 AND a.assignee_id = ?
                 AND a.status = 'pending'
               ORDER BY a.created_at DESC""",
            (org_id,)
        ).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        item["days_remaining"] = calculate_days_remaining(item.get("created_at"))
        result.append(item)
    return result


def get_assignment_with_ownership_check(assignment_id, org_id):
    """Return an assignment dict if it exists and belongs to the given university, else None."""
    with get_db() as db:
        row = db.execute(
            """SELECT a.*, p.title as problem_title
               FROM assignments a
               JOIN problems p ON p.id = a.problem_id
               WHERE a.id = ?
                 AND a.assignee_type = 'university'
                 AND a.assignee_id = ?""",
            (assignment_id, org_id)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def get_assignment_for_admin(assignment_id):
    """Return an assignment dict for admin access."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM assignments WHERE id = ?", (assignment_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def accept_assignment(assignment_id, org_id, user_id):
    """Accept a pending challenge/assignment. Returns (success, error_message)."""
    assignment = get_assignment_with_ownership_check(assignment_id, org_id)
    if not assignment:
        return False, "Assignment not found or not owned by this university"

    if assignment["status"] != "pending":
        return False, f"Cannot accept assignment with status '{assignment['status']}'"

    Assignment.update_status(assignment_id, "accepted")

    # Notify admin who created the assignment
    payload = json.dumps({
        "assignment_id": assignment_id,
        "problem_id": assignment["problem_id"],
        "status": "accepted",
        "message": "University accepted the challenge"
    })
    _notify_assignment_actors(assignment["created_by"], "status_changed", payload)

    audit_log(user_id, "assignment_accepted", "assignment", assignment_id,
              {"problem_id": assignment["problem_id"], "org_id": org_id})
    return True, None


def decline_assignment(assignment_id, org_id, user_id, reason):
    """Decline a pending challenge with a reason. Returns (success, error_message)."""
    if not reason or not reason.strip():
        return False, "Decline reason is required"

    assignment = get_assignment_with_ownership_check(assignment_id, org_id)
    if not assignment:
        return False, "Assignment not found or not owned by this university"

    if assignment["status"] != "pending":
        return False, f"Cannot decline assignment with status '{assignment['status']}'"

    Assignment.update_status(assignment_id, "rejected")

    payload = json.dumps({
        "assignment_id": assignment_id,
        "problem_id": assignment["problem_id"],
        "status": "rejected",
        "reason": reason,
        "message": "University declined the challenge"
    })
    _notify_assignment_actors(assignment["created_by"], "status_changed", payload)

    audit_log(user_id, "assignment_declined", "assignment", assignment_id,
              {"problem_id": assignment["problem_id"], "org_id": org_id, "reason": reason})
    return True, None


def get_history_for_problem(problem_id):
    """Return full audit trail for all assignments of a given problem."""
    with get_db() as db:
        rows = db.execute(
            """SELECT a.*, al.actor_id, al.action, al.payload_json, al.created_at as log_time,
                      u.name as actor_name, u.role as actor_role
               FROM assignments a
               LEFT JOIN audit_log al
                 ON al.target_type = 'assignment'
                AND al.target_id = a.id
               LEFT JOIN users u ON u.id = al.actor_id
               WHERE a.problem_id = ?
               ORDER BY a.created_at DESC, al.created_at ASC""",
            (problem_id,)
        ).fetchall()

    history = []
    seen = set()
    for row in rows:
        item = dict(row)
        entry_id = (item["id"], item.get("log_time"))
        if entry_id not in seen:
            seen.add(entry_id)
            history.append(item)
    return history


def calculate_days_remaining(created_at_str):
    """Calculate approximate days remaining from assignment creation using default deadline."""
    if not created_at_str:
        return DEFAULT_DEADLINE_DAYS
    try:
        created = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        deadline = created + timedelta(days=DEFAULT_DEADLINE_DAYS)
        remaining = (deadline - datetime.now()).days
        return max(0, remaining)
    except Exception:
        return DEFAULT_DEADLINE_DAYS


def auto_assign_top_university(problem_id):
    """Auto-assign the top-ranked university match after AI analysis completes."""
    from ai.matcher import match_universities
    from database.db import get_db
    # Fetch problem details for matching
    with get_db() as db:
        row = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not row:
            return None
        problem = dict(row)
    # Get match results (already include rank after matcher update)
    matches = match_universities(problem)
    if not matches:
        return None
    top = matches[0]
    # Create assignment to top university
    Assignment.create(
        problem_id=problem_id,
        assignee_type='university',
        assignee_id=top["university_id"],
        created_by=None,
        notes=f"Auto-assigned top match (rank {top.get('rank', 1)})"
    )
    return top


def _notify_assignment_actors(actor_id, notif_type, payload):
    """Send a notification to a user if actor_id is valid."""
    if actor_id:
        try:
            Notification.create(actor_id, notif_type, payload)
        except Exception:
            pass  # Don't fail the main operation for notification errors
