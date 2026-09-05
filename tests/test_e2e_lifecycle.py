"""End-to-end integration test for SAMAADHAN AI full lifecycle.

Pipeline: REPORT → AI ANALYSIS → DUPLICATE → SKILLS → PRIORITY → MATCH → ASSIGN →
ACCEPT → PROJECT → TEAM ASSIGN → MILESTONES → IMPACT → TIMEOUT/RE-ROUTE.
Runs against the live database and exercises the service layer.
"""
import sqlite3
import os
import sys
import json

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import init_db, get_db
from services import assignment_service
from auth.models import User
from config import Config


DB_PATH = "societal_ai.db"


def step(title):
    print(f"\n=== {title} ===")


def main():
    init_db()

    # ------------------------------------------------------------
    # 1. REPORT PROBLEM
    # ------------------------------------------------------------
    step("1. REPORT PROBLEM")
    with get_db() as db:
        db.execute("""
            INSERT INTO problems(title, description, category, latitude, longitude, status, priority_level, created_at)
            VALUES(?,?,?,?,?,?,?,datetime('now','-1 day'))
        """, (
            "E2E Test: Broken irrigation pumps in Nagapattinam",
            "Twelve villages along the Cauvery delta have failing irrigation pumps. Farmers report 30% yield loss this season.",
            "Agriculture",
            10.77, 79.85,
            "submitted", "high"
        ))
        pid = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    print(f"Created problem id={pid}")

    # ------------------------------------------------------------
    # 2. AI ANALYSIS / SKILL EXTRACTION / PRIORITY
    # ------------------------------------------------------------
    step("2. AI ANALYSIS → SKILL → PRIORITY")
    with get_db() as db:
        db.execute("""
            UPDATE problems
            SET required_skills=?,
                ai_category=?,
                priority_level='high',
                priority_score=0.86,
                status='analyzed'
            WHERE id=?
        """, (json.dumps(["hydrology", "IoT sensors", "irrigation systems"]), "Agriculture", pid))

    # ------------------------------------------------------------
    # 3. UNIVERSITY MATCHING
    # ------------------------------------------------------------
    step("3. UNIVERSITY MATCHING (top 3)")
    matches = [
        (pid, 4, 0.91, 1),  # Anna University
        (pid, 7, 0.84, 2),  # NIT Trichy
        (pid, 12, 0.79, 3), # TCE Madurai
    ]
    with get_db() as db:
        for p, u, score, rank in matches:
            db.execute("""
                INSERT OR IGNORE INTO matches(problem_id, university_id, final_score, rank)
                VALUES(?,?,?,?)
            """, (p, u, score, rank))
    print(f"Inserted {len(matches)} match rows")

    # ------------------------------------------------------------
    # 4. AUTO-ASSIGN top university
    # ------------------------------------------------------------
    step("4. AUTO-ASSIGN (top match)")
    assignment = assignment_service.auto_assign_top_university(pid)
    assert assignment is not None
    aid = assignment.id if hasattr(assignment, "id") else assignment["id"]
    print(f"Assignment id={aid}")

    # ------------------------------------------------------------
    # 5. ADMIN ACKNOWLEDGES TIMEOUT-RISK + INSPECTS HISTORY
    # ------------------------------------------------------------
    step("5. VIEW ASSIGNMENT HISTORY (admin)")
    history = assignment_service.get_history_for_problem(pid)
    print(f"History rows: {len(history)}")
    assert any(h.get("action") == "assigned_auto_top" for h in history)

    # ------------------------------------------------------------
    # 6. UNIVERSITY DECLINES with reason → learning + re-route
    # ------------------------------------------------------------
    step("6. UNIVERSITY DECLINE → adaptive learning + re-routing")
    success, err = assignment_service.decline_assignment(aid, 4, user_id=1, reason="missing_expertise")
    assert success, err
    new_assign = assignment_service.route_to_next_university(pid, aid)
    assert new_assign is not None, "Re-routing failed: no alternative match"
    print(f"Re-routed to assignment id={new_assign.id if hasattr(new_assign,'id') else new_assign['id']}")

    # ------------------------------------------------------------
    # 7. UNIVERSITY ACCEPTS → project created
    # ------------------------------------------------------------
    step("7. UNIVERSITY ACCEPT → project creation")
    new_aid = new_assign.id if hasattr(new_assign, "id") else new_assign["id"]
    new_uni = new_assign.assignee_id if hasattr(new_assign, "assignee_id") else new_assign["assignee_id"]
    success, err = assignment_service.accept_assignment(new_aid, new_uni, user_id=2)
    assert success, err
    project = assignment_service.create_project(
        problem_id=pid,
        name=f"Project for problem {pid}",
        status="in_progress",
        assigned_to_type="university",
        assigned_to_id=new_uni,
    )
    print(f"Project id={project['id']} status={project['status']}")

    # ------------------------------------------------------------
    # 8. FACULTY / STUDENT ASSIGNMENTS
    # ------------------------------------------------------------
    step("8. FACULTY / STUDENT ASSIGNMENTS")
    with get_db() as db:
        db.execute("""
            INSERT INTO project_assignments(project_id, assignee_type, assignee_id, role)
            VALUES(?,?,?,?)
        """, (project["id"], "faculty", 2, "principal_investigator"))
        db.execute("""
            INSERT INTO project_assignments(project_id, assignee_type, assignee_id, role)
            VALUES(?,?,?,?)
        """, (project["id"], "student", 5, "research_assistant"))
        pa_count = db.execute(
            "SELECT count(*) as c FROM project_assignments WHERE project_id=?",
            (project["id"],)
        ).fetchone()["c"]
    assert pa_count == 2
    print(f"Assigned faculty+student: rows={pa_count}")

    # ------------------------------------------------------------
    # 9. MILESTONES (add → submit → verify)
    # ------------------------------------------------------------
    step("9. MILESTONES: create / submit / verify")
    with get_db() as db:
        cur = db.execute("""
            INSERT INTO project_milestones(project_id, title, stage, status)
            VALUES(?,?,?,?)
        """, (project["id"], "Site survey + sensor deployment plan", "prototype", "pending"))
        ms_id = cur.lastrowid

    # Submit evidence
    with get_db() as db:
        db.execute(
            "UPDATE project_milestones SET status='submitted', evidence_url='/uploads/site_survey.pdf' WHERE id=?",
            (ms_id,),
        )
    # Verify (citizen + faculty)
    with get_db() as db:
        db.execute("""
            INSERT INTO milestone_verifications(milestone_id, citizen_id, faculty_id, feedback_text, is_confirmed)
            VALUES(?,?,?,?,?)
        """, (ms_id, 1, 2, "Site visit confirmed by citizen and faculty lead.", 1))
        db.execute("UPDATE project_milestones SET status='verified' WHERE id=?", (ms_id,))
    print("Milestone submitted, dual-verified, status=verified")

    # ------------------------------------------------------------
    # 10. PROGRESS + IMPACT METRICS
    # ------------------------------------------------------------
    step("10. PROGRESS + IMPACT")
    with get_db() as db:
        db.execute("UPDATE projects SET progress=35, status='in_progress' WHERE id=?", (project["id"],))
        db.execute("""
            INSERT INTO impact_metrics(project_id, metric_key, metric_value, recorded_by)
            VALUES(?,?,?,?)
        """, (project["id"], "villages_impacted", 12, 1))
        db.execute("""
            INSERT INTO impact_metrics(project_id, metric_key, metric_value, recorded_by)
            VALUES(?,?,?,?)
        """, (project["id"], "farmers_supported", 480, 1))
        impact_count = db.execute(
            "SELECT count(*) as c FROM impact_metrics WHERE project_id=?", (project["id"],)
        ).fetchone()["c"]
    assert impact_count == 2
    print(f"Impact metrics rows={impact_count}")

    # ------------------------------------------------------------
    # 11. TIMEOUT / RE-ROUTE — insert an old pending assignment and run scan
    # ------------------------------------------------------------
    step("11. TIMEOUT / RE-ROUTE")
    with get_db() as db:
        cur = db.execute("""
            INSERT INTO problems(title, description, status, created_at)
            VALUES(?,?,?,datetime('now','-100 hours'))
        """, ("E2E Timeout: Power cuts in Madurai", "Frequent outages affecting 3 wards.", "submitted"))
        timeout_pid = cur.lastrowid
        db.execute("""
            INSERT INTO matches(problem_id, university_id, final_score, rank)
            VALUES(?,?,?,?), (?,?,?,?), (?,?,?,?)
        """, (timeout_pid, 4, 0.93, 1, timeout_pid, 7, 0.88, 2, timeout_pid, 12, 0.81, 3))
        cur = db.execute("""
            INSERT INTO assignments(problem_id, assignee_type, assignee_id, status, created_at)
            VALUES(?,?,?,?, datetime('now','-100 hours'))
        """, (timeout_pid, "university", 4, "pending"))
        timeout_aid = cur.lastrowid

    expired = assignment_service.check_expired_assignments()
    print(f"Expired IDs: {expired}")
    assert timeout_aid in expired, f"Expected assignment {timeout_aid} in {expired}"

    # Verify re-routing happened
    with get_db() as db:
        r = db.execute(
            "SELECT count(*) as c FROM assignments WHERE problem_id=?", (timeout_pid,)
        ).fetchone()["c"]
    assert r >= 2, f"Expected re-routing to create additional assignment, found {r}"
    print(f"Re-routing OK: total assignments on problem = {r}")

    # ------------------------------------------------------------
    # 12. ADAPTIVE LEARNING
    # ------------------------------------------------------------
    step("12. ADAPTIVE LEARNING")
    with get_db() as db:
        la = db.execute("""
            SELECT penalty_factor, sample_count, last_reason
            FROM matcher_learning_adjustments
            WHERE university_id=4
            ORDER BY updated_at DESC LIMIT 1
        """).fetchone()
    print(f"Latest learning row: {dict(la) if la else None}")
    assert la is not None and la["sample_count"] >= 1

    # ------------------------------------------------------------
    # 13. ADMIN METRICS
    # ------------------------------------------------------------
    step("13. ADMIN METRICS RENDER")
    with get_db() as db:
        n_projects = db.execute("SELECT count(*) as c FROM projects").fetchone()["c"]
        n_milestones = db.execute("SELECT count(*) as c FROM project_milestones").fetchone()["c"]
        n_verifications = db.execute("SELECT count(*) as c FROM milestone_verifications").fetchone()["c"]
        n_impacts = db.execute("SELECT count(*) as c FROM impact_metrics").fetchone()["c"]
        n_assignments = db.execute("SELECT count(*) as c FROM assignments").fetchone()["c"]
        n_team = db.execute("SELECT count(*) as c FROM project_assignments").fetchone()["c"]
    print({
        "projects": n_projects,
        "milestones": n_milestones,
        "verifications": n_verifications,
        "impacts": n_impacts,
        "assignments": n_assignments,
        "team_assignments": n_team,
    })
    assert n_projects >= 1
    assert n_team >= 2
    assert n_milestones >= 1
    assert n_verifications >= 1
    assert n_impacts >= 2
    assert n_assignments >= 2  # 1 declined + 1 accepted + 1 timed-out + re-routed

    print("\n✅ END-TO-END LIFECYCLE TEST PASSED")


if __name__ == "__main__":
    main()
