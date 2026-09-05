"""Assignment and re-routing service layer.
Reference: Section I pseudocode (auto-assign, handle-response, route, timeout scanner).
Uses database transactions for atomicity. Respects UNIVERSITY_RESPONSE_TIMEOUT_HOURS
and MAX_ASSIGNMENT_ROUNDS limits.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from database.db import get_db
from config import Config
from models.assignment import Assignment
from models.notification import Notification

# Config-driven safety limits
UNIVERSITY_RESPONSE_TIMEOUT_HOURS = getattr(Config, 'UNIVERSITY_RESPONSE_TIMEOUT_HOURS', 48)
MAX_ASSIGNMENT_ROUNDS = getattr(Config, 'MAX_ASSIGNMENT_ROUNDS', 3)


def get_assignment(assignment_id):
    """Fetch an assignment by id with full row details."""
    with get_db() as db:
        row = db.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        if not row:
            return None
        return Assignment(**dict(row))


def verify_university_owns_assignment(assignment_id, university_id):
    """Confirm the assignment belongs to the given university and is pending."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return False
    return (
        assignment.assignee_type == 'university'
        and assignment.assignee_id == university_id
        and assignment.status in ('pending',)
    )


def log_history(assignment_id, action, actor_id=None, reason=None):
    """Log every state transition to assignment_history (atomic with parent tx)."""
    with get_db() as db:
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS assignment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    actor_id INTEGER,
                    reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assignment_id) REFERENCES assignments(id)
                )
            """)
        except Exception:
            pass
        if assignment_id is not None:
            db.execute(
                "INSERT INTO assignment_history(assignment_id, action, actor_id, reason) VALUES(?,?,?,?)",
                (assignment_id, action, actor_id, reason)
            )


def send_notification(user_id, notification_type, payload_json):
    """Send in-app notification (wraps model create with payload validation)."""
    if notification_type not in Notification.TYPES:
        notification_type = 'status_changed'
    return Notification.create(user_id, notification_type, payload_json or '{}')


def update_problem_status(problem_id, new_status):
    """Update problem status atomically."""
    with get_db() as db:
        db.execute(
            "UPDATE problems SET status=? WHERE id=?",
            (new_status, problem_id)
        )


def create_project(problem_id, name, status='proposed', assigned_to_type=None, assigned_to_id=None):
    """Create a project record linked to a problem."""
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO projects(problem_id, name, status, assigned_to_type, assigned_to_id)
               VALUES(?,?,?,?,?)""",
            (problem_id, name, status, assigned_to_type, assigned_to_id)
        )
        pid = cur.lastrowid
        row = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(row)


def auto_assign_top_university(problem_id):
    """Assign rank 1 university after matching (Section I: auto-assign top match)."""
    with get_db() as db:
        match_row = db.execute(
            """SELECT university_id, final_score FROM matches
               WHERE problem_id=? ORDER BY final_score DESC LIMIT 1""",
            (problem_id,)
        ).fetchone()

        if not match_row:
            log_history(None, 'auto_assign_failed', reason='no_match')
            return None

        university_id = match_row['university_id']
        existing = db.execute(
            "SELECT id FROM assignments WHERE problem_id=? AND assignee_type='university' AND assignee_id=? AND status='pending'",
            (problem_id, university_id)
        ).fetchone()

        if existing:
            return get_assignment(existing['id'])

        assignment = Assignment.create(
            problem_id=problem_id,
            assignee_type='university',
            assignee_id=university_id,
            created_by=None,
            notes='Auto-assigned: rank 1 match'
        )

        log_history(assignment.id, 'assigned_auto_top', reason='rank_1_match')
        update_problem_status(problem_id, 'assigned')

        university_user = db.execute(
            "SELECT id FROM users WHERE role='university' AND org_id=? LIMIT 1", (university_id,)
        ).fetchone()
        if university_user:
            send_notification(
                university_user['id'],
                'assignment_created',
                json.dumps({'problem_id': problem_id, 'assignment_id': assignment.id, 'message': 'You have been assigned a new problem'})
            )

        return assignment


def record_learning_adjustment(university_id, category, reason):
    """Record adaptive learning adjustment based on decline reason.

    Updates matcher_learning_adjustments with penalty factors derived from
    categorized decline reasons to improve future matching accuracy.
    """
    # Map decline reasons to penalty adjustments
    penalty_map = {
        'capacity_full': 0.85,          # Moderate penalty - temporary constraint
        'missing_expertise': 0.60,      # Strong penalty - skill mismatch
        'out_of_scope': 0.55,           # Strong penalty - domain mismatch
        'no_lab_equipment': 0.70,       # Significant penalty - capability gap
        'low_priority': 0.90,           # Light penalty - preference issue
        'other': 0.95                   # Minimal penalty - unclear signal
    }

    penalty_factor = penalty_map.get(reason, 0.95)

    with get_db() as db:
        # Check if adjustment exists
        existing = db.execute(
            """SELECT id, penalty_factor, sample_count FROM matcher_learning_adjustments
               WHERE university_id=? AND (category=? OR (category IS NULL AND ? IS NULL))""",
            (university_id, category, category)
        ).fetchone()

        if existing:
            # Exponential moving average: new_penalty = 0.7 * old + 0.3 * incoming
            new_penalty = 0.7 * existing['penalty_factor'] + 0.3 * penalty_factor
            new_count = existing['sample_count'] + 1
            db.execute(
                """UPDATE matcher_learning_adjustments
                   SET penalty_factor=?, sample_count=?, last_reason=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (new_penalty, new_count, reason, existing['id'])
            )
        else:
            # Create new adjustment entry
            db.execute(
                """INSERT INTO matcher_learning_adjustments
                   (university_id, category, skill_name, penalty_factor, sample_count, last_reason)
                   VALUES (?, ?, NULL, ?, 1, ?)""",
                (university_id, category, penalty_factor, reason)
            )


def handle_university_response(assignment_id, action, reason=None):
    """Accept/decline handler with atomic updates (Section I: response handler)."""
    action = action.lower() if isinstance(action, str) else action
    if action not in ('accept', 'decline', 'accepted', 'rejected'):
        raise ValueError("action must be 'accept', 'decline', 'accepted', or 'rejected'")

    if action in ('accept', 'accepted'):
        new_status = 'accepted'
    else:
        new_status = 'rejected'

    with get_db() as db:
        assignment = get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")

        if assignment.status != 'pending':
            raise ValueError(f"Assignment status is '{assignment.status}'; cannot respond")

        Assignment.update_status(assignment_id, new_status)
        log_history(assignment_id, f'response_{new_status}', reason=reason or action)

        if new_status == 'rejected':
            # Record learning adjustment for adaptive matching
            if reason:
                problem_row = db.execute(
                    "SELECT category FROM problems WHERE id=?",
                    (assignment.problem_id,)
                ).fetchone()
                problem_category = problem_row['category'] if problem_row else None
                record_learning_adjustment(assignment.assignee_id, problem_category, reason)

            update_problem_status(assignment.problem_id, 'pending_reassignment')
            admin = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
            if admin:
                send_notification(
                    admin['id'],
                    'status_changed',
                    json.dumps({'assignment_id': assignment_id, 'problem_id': assignment.problem_id, 'reason': reason or 'declined'})
                )

        if new_status == 'accepted':
            update_problem_status(assignment.problem_id, 'in_progress')
            problem_row = db.execute("SELECT title FROM problems WHERE id=?", (assignment.problem_id,)).fetchone()
            if problem_row:
                proj_name = f"Project for {problem_row['title']}"
                create_project(
                    problem_id=assignment.problem_id,
                    name=proj_name,
                    status='in_progress',
                    assigned_to_type='university',
                    assigned_to_id=assignment.assignee_id
                )
            university_user = db.execute(
                "SELECT id FROM users WHERE role='university' AND org_id=? LIMIT 1", (assignment.assignee_id,)
            ).fetchone()
            if university_user:
                send_notification(
                    university_user['id'],
                    'status_changed',
                    json.dumps({'assignment_id': assignment_id, 'new_status': 'accepted'})
                )

        return get_assignment(assignment_id)


def route_to_next_university(problem_id, current_assignment_id):
    """Re-routing logic: find next best match and assign if under MAX_ASSIGNMENT_ROUNDS."""
    with get_db() as db:
        existing_assignments = db.execute(
            "SELECT id FROM assignments WHERE problem_id=? AND assignee_type='university'", (problem_id,)
        ).fetchall()

        rounds_used = len(existing_assignments)
        if rounds_used >= MAX_ASSIGNMENT_ROUNDS:
            log_history(current_assignment_id, 'route_blocked', reason=f'max_rounds_reached_{MAX_ASSIGNMENT_ROUNDS}')
            return None

        current = get_assignment(current_assignment_id)
        excluded_university_id = current.assignee_id if current else None

        query = """SELECT university_id, final_score FROM matches
                  WHERE problem_id=?"""
        params = [problem_id]
        if excluded_university_id:
            query += " AND university_id != ?"
            params.append(excluded_university_id)
        query += " ORDER BY final_score DESC LIMIT 1"

        next_match = db.execute(query, params).fetchone()

        if not next_match:
            log_history(current_assignment_id, 'route_failed', reason='no_alternative_match')
            return None

        next_uni_id = next_match['university_id']

        existing = db.execute(
            "SELECT id FROM assignments WHERE problem_id=? AND assignee_type='university' AND assignee_id=?",
            (problem_id, next_uni_id)
        ).fetchone()

        if existing:
            return get_assignment(existing['id'])

        new_assignment = Assignment.create(
            problem_id=problem_id,
            assignee_type='university',
            assignee_id=next_uni_id,
            created_by=None,
            notes=f'Routed from assignment {current_assignment_id} (round {rounds_used + 1})'
        )

        log_history(new_assignment.id, 'routed_from', reason=f'previous_assignment_{current_assignment_id}')
        log_history(current_assignment_id, 'routed_to_next', reason=f'new_assignment_{new_assignment.id}')

        university_user = db.execute(
            "SELECT id FROM users WHERE role='university' AND org_id=? LIMIT 1", (next_uni_id,)
        ).fetchone()
        if university_user:
            send_notification(
                university_user['id'],
                'assignment_created',
                json.dumps({'problem_id': problem_id, 'assignment_id': new_assignment.id, 'message': 'You have been assigned after re-routing'})
            )

        return new_assignment


def check_expired_assignments():
    """Timeout scanner: find pending assignments older than UNIVERSITY_RESPONSE_TIMEOUT_HOURS."""
    timeout_hours = UNIVERSITY_RESPONSE_TIMEOUT_HOURS
    cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)
    cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

    expired_ids = []
    with get_db() as db:
        rows = db.execute(
            """SELECT id, problem_id, assignee_id FROM assignments
                WHERE status='pending' AND created_at < ?""",
            (cutoff_str,)
        ).fetchall()

        for row in rows:
            assignment_id = row['id']
            problem_id = row['problem_id']
            assignee_id = row['assignee_id']

            log_history(assignment_id, 'expired', reason=f'timeout_after_{timeout_hours}h')
            Assignment.update_status(assignment_id, 'rejected')
            update_problem_status(problem_id, 'pending_reassignment')

            existing = db.execute(
                "SELECT count(*) as cnt FROM assignments WHERE problem_id=?", (problem_id,)
            ).fetchone()
            if existing and existing['cnt'] < MAX_ASSIGNMENT_ROUNDS:
                try:
                    route_to_next_university(problem_id, assignment_id)
                except Exception:
                    pass

            university_user = db.execute(
                "SELECT id FROM users WHERE role='university' AND org_id=? LIMIT 1", (assignee_id,)
            ).fetchone()
            if university_user:
                send_notification(
                    university_user['id'],
                    'status_changed',
                    json.dumps({'assignment_id': assignment_id, 'new_status': 'rejected', 'reason': 'timeout'})
                )

            expired_ids.append(assignment_id)

    return expired_ids
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


DEFAULT_DEADLINE_DAYS = 3


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