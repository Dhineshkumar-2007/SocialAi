"""Visual browser demo of the university flow against the LIVE app.

Drives the real UI in a headed Chromium window so you can watch:

  REPORT (seeded) -> UNIV REGISTER (UI) -> AUTO-LOGIN DASHBOARD ->
  CHALLENGE DETAIL -> ACCEPT (project + 6 milestones) ->
  SECOND CHALLENGE DECLINE (with reason, learning recorded)

Requires the Flask server running on http://127.0.0.1:5000 and the real DB.
Uses a dedicated fake institution so real data is never touched.
Screenshots are written to <repo>/scripts/screenshots/.
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "societal_ai.db"
BASE = "http://127.0.0.1:5000"
SHOT_DIR = ROOT / "scripts" / "screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

FAKE_UNI_NAME = "E2E Visual University (Fake)"
FAKE_UNI_EMAIL = "registrar@e2efake.edu"
FAKE_UNI_PW = "VisualPass123!"
FAKE_EMAIL_DOMAIN = "e2efake.edu"

cen = 0
def shot(page, name):
    global cen
    cen += 1
    path = SHOT_DIR / f"{cen:02d}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  screenshot: {path}")
    return path


def clean_prior_data(db):
    db.execute("DELETE FROM assignments WHERE assignee_type='university' AND assignee_id IN "
               "(SELECT id FROM universities WHERE name=?)", (FAKE_UNI_NAME,))
    db.execute("DELETE FROM problem_university_matches WHERE problem_id IN "
               "(SELECT id FROM problems WHERE title LIKE 'E2E Visual:%')")
    db.execute("DELETE FROM matches WHERE problem_id IN "
               "(SELECT id FROM problems WHERE title LIKE 'E2E Visual:%')")
    proj = [r[0] for r in db.execute(
        "SELECT id FROM projects WHERE problem_id IN "
        "(SELECT id FROM problems WHERE title LIKE 'E2E Visual:%')").fetchall()]
    for pid in proj:
        db.execute("DELETE FROM project_milestones WHERE project_id=?", (pid,))
    if proj:
        db.execute("DELETE FROM projects WHERE id IN (%s)" % ",".join("?" * len(proj)), proj)
    db.execute("DELETE FROM evidence WHERE problem_id IN "
               "(SELECT id FROM problems WHERE title LIKE 'E2E Visual:%')")
    db.execute("DELETE FROM problems WHERE title LIKE 'E2E Visual:%'")
    db.execute("DELETE FROM users WHERE email=?", (FAKE_UNI_EMAIL,))
    db.execute("DELETE FROM users WHERE org_id IN (SELECT id FROM universities WHERE name=?)",
               (FAKE_UNI_NAME,))
    db.execute("DELETE FROM institution_research_areas WHERE university_id IN "
               "(SELECT id FROM universities WHERE name=?)", (FAKE_UNI_NAME,))
    db.execute("DELETE FROM universities WHERE name=?", (FAKE_UNI_NAME,))


def seed(db):
    cur = db.execute("""
        INSERT INTO universities(name, city, description, capacity, verified,
                                 institution_type, website, address, state,
                                 email_domain, research_summary, expertise_summary)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        FAKE_UNI_NAME, "Madurai",
        "Fake institution used to visually demo the university accept/decline flow.",
        50, 1, "university", "https://e2efake.edu",
        "E2E Demo Building, Madurai, Tamil Nadu", "Tamil Nadu",
        FAKE_EMAIL_DOMAIN,
        "Water quality, sanitation engineering, transport and civic infrastructure.",
        "Environmental engineering, hydrology, water treatment, structural civil works."
    ))
    uni_id = cur.lastrowid
    db.execute(
        "INSERT INTO institution_research_areas(university_id, area, keywords) VALUES(?,?,?)",
        (uni_id, "Water quality", "contamination, groundwater, drinking water, treatment"))
    db.execute(
        "INSERT INTO institution_research_areas(university_id, area, keywords) VALUES(?,?,?)",
        (uni_id, "Civic infrastructure", "streetlights, roads, drainage, public utilities"))

    problems = [
        ("E2E Visual: Drinking water contamination in Vilacheri village, Madurai",
         "Dozens of families near the Vilacheri borewell have no safe drinking water. "
         "Recent tests show high contamination and several residents report stomach illness. "
         "Urgent water quality testing and a treatment plan are needed.",
         "Water and sanitation", "high", 9.9589, 78.1550, "Madurai"),
        ("E2E Visual: Non-functional streetlights on Highway road, Madurai",
         "All streetlight poles along the Highway stretch have been dark for two weeks. "
         "The road is unlit after sunset, causing accidents and unsafe conditions for "
         "pedestrians and two-wheelers.",
         "Infrastructure", "medium", 9.9252, 78.1198, "Madurai"),
    ]
    problem_ids = []
    for (title, desc, cat, prio, lat, lng, district) in problems:
        cur = db.execute("""
            INSERT INTO problems(title, description, category, priority_level,
                                 status, latitude, longitude, district, address)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (title, desc, cat, prio, "assigned", lat, lng, district, "Madurai, Tamil Nadu"))
        pid = cur.lastrowid
        problem_ids.append(pid)
        db.execute("""
            INSERT INTO problem_university_matches(problem_id, university_id,
                                                   final_score, explanation, rank)
            VALUES(?,?,?,?,1)
        """, (pid, uni_id, 0.91 if cat == "Water and sanitation" else 0.84,
              json.dumps({
                  "domain": 0.9, "research": 0.85, "faculty": 0.8,
                  "lab": 0.75, "capacity": 0.9,
              })))
        db.execute("""
            INSERT INTO assignments(problem_id, assignee_type, assignee_id, status,
                                    notes, created_at)
            VALUES(?,?,?,?,?,datetime('now'))
        """, (pid, "university", uni_id, "pending",
              f"Auto-routed to {FAKE_UNI_NAME} (rank 1, score 0.9)"))
    db.commit()
    return uni_id, problem_ids


def db_assert(desc, actual, expected, ok):
    flag = "OK" if ok else "FAIL"
    print(f"  [assert] {desc}: got={actual} expected={expected} -> {flag}")
    if not ok:
        raise AssertionError(f"{desc}: got {actual} expected {expected}")


def main():
    with sqlite3.connect(str(DB_PATH)) as db:
        clean_prior_data(db)
        db.commit()
        fake_uni_id, (pid1, pid2) = seed(db)

    print("Seeded fake university id:", fake_uni_id)
    print("Seeded problems:", pid1, pid2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=250)
        ctx = browser.new_context(viewport={"width": 1440, "height": 920},
                                  locale="en-US")
        page = ctx.new_page()

        # ---------------- 1. REGISTER (UI) ----------------
        page.goto(f"{BASE}/university/register")
        print("== 1. HEI REGISTER PAGE ==")
        page.wait_for_selector(f"#org option[value='{fake_uni_id}']", timeout=15000)
        print("  institution dropdown loaded (incl. fake university)")
        page.fill("#name", "Dr. E2E Registrar")
        page.fill("#email", FAKE_UNI_EMAIL)
        page.select_option("#org", str(fake_uni_id))
        page.fill("#password", FAKE_UNI_PW)
        page.fill("#password2", FAKE_UNI_PW)
        shot(page, "university_register")
        page.click("#submitBtn")
        print("  submitted registration -> waiting for auto-login redirect to /university")
        page.wait_for_url("**/university", timeout=20000)
        shot(page, "university_dashboard_after_register")

        # ---------------- 2. DASHBOARD: incoming pending ----------------
        print("== 2. UNIVERSITY DASHBOARD (incoming challenges) ==")
        page.wait_for_selector(".assignment-card", timeout=20000)
        body = page.locator("#assignmentList").inner_text()
        assert "Drinking water contamination" in body, "problem 1 not on dashboard"
        assert "Non-functional streetlights" in body, "problem 2 not on dashboard"
        m_pending = page.locator("#m-pending").inner_text().strip()
        db_assert("pending-review metric", m_pending, "2", m_pending == "2")
        shot(page, "dashboard_incoming")
        print("  both challenges visible with AI match bars")

        # ---------------- 3. CHALLENGE DETAIL ----------------
        print("== 3. CHALLENGE DETAIL ==")
        page.locator(".assignment-card").nth(0).locator("a.btn-primary").click()
        page.wait_for_url("**/university/challenges/*", timeout=15000)
        page.wait_for_selector("#acceptBtn", timeout=15000)
        page.wait_for_function(
            "document.getElementById('sub').textContent.includes('Drinking water')",
            timeout=15000)
        sub_text = page.locator("#sub").inner_text()
        assert "Water and sanitation" in sub_text, sub_text
        shot(page, "challenge_detail_accept")
        print("  challenge detail loaded:", sub_text)

        # ---------------- 4. ACCEPT ----------------
        print("== 4. ACCEPT CHALLENGE ==")
        page.click("#acceptBtn")
        page.wait_for_function(
            "document.getElementById('actionMsg').textContent.includes('accepted')",
            timeout=20000)
        shot(page, "accept_success")
        page.wait_for_url("**/university", timeout=20000)
        page.wait_for_selector("#projectList", timeout=15000)
        page.wait_for_function(
            "document.getElementById('projectList').textContent.includes('Drinking water')",
            timeout=20000)
        shot(page, "dashboard_after_accept")
        print("  accepted -> project now listed under 'Active projects'")

        with sqlite3.connect(str(DB_PATH)) as db:
            a = db.execute("SELECT status FROM assignments WHERE problem_id=?", (pid1,)).fetchone()
            pr = db.execute("SELECT status FROM problems WHERE id=?", (pid1,)).fetchone()
            proj = db.execute(
                "SELECT id, status FROM projects WHERE problem_id=? AND assigned_to_id=?",
                (pid1, fake_uni_id)).fetchone()
            ms = db.execute(
                "SELECT COUNT(*) FROM project_milestones WHERE project_id=?",
                (proj[0],)).fetchone()[0] if proj else -1
            db_assert("assignment status", a[0], "accepted", a[0] == "accepted")
            db_assert("problem status", pr[0], "in_progress", pr[0] == "in_progress")
            db_assert("project created", None if proj is None else proj[0],
                      "project", proj is not None and proj[1] == "in_progress")
            db_assert("milestones seed", ms, 6, ms == 6)

        # ---------------- 5. DECLINE (second challenge) ----------------
        print("== 5. DECLINE SECOND CHALLENGE ==")
        page.locator(".assignment-card").nth(0).locator("a.btn-primary").click()
        page.wait_for_url("**/university/challenges/*", timeout=15000)
        page.wait_for_function(
            "document.getElementById('sub').textContent.includes('Streetlights')",
            timeout=15000)
        shot(page, "challenge_detail_decline")
        page.click("button:text-is('Decline')")
        page.wait_for_selector("#declineForm", state="visible", timeout=10000)
        page.check("input[name='reason'][value='expertise']")
        page.click("button:text-is('Confirm Decline')")
        page.wait_for_function(
            "document.getElementById('actionMsg').textContent.includes('route to the next best match')",
            timeout=20000)
        shot(page, "decline_success")
        print("  declined with 'Expertise mismatch'")

        with sqlite3.connect(str(DB_PATH)) as db:
            a2 = db.execute(
                "SELECT status, decline_reason FROM assignments WHERE problem_id=? AND status='rejected'",
                (pid2,)).fetchone()
            pr2 = db.execute("SELECT status FROM problems WHERE id=?", (pid2,)).fetchone()
            adj = db.execute(
                "SELECT penalty_factor FROM matcher_learning_adjustments WHERE university_id=?",
                (fake_uni_id,)).fetchone()
            db_assert("assignment status", a2[0] if a2 else None, "rejected",
                      a2 is not None and a2[0] == "rejected")
            db_assert("decline reason", a2[1] if a2 else None, "expertise",
                      a2 is not None and a2[1] == "expertise")
            db_assert("problem status", pr2[0], "pending_reassignment", pr2[0] == "pending_reassignment")
            db_assert("learning adjustment recorded", adj[0] if adj else None,
                      "<1", adj is not None and adj[0] < 1)

        browser.close()

    print()
    print("== VISUAL UNIVERSITY FLOW PASSED ==")
    print(f"screenshots in: {SHOT_DIR}")


if __name__ == "__main__":
    main()