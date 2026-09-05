"""End-to-end API flow test: university registration → citizen reporting →
AI analysis + auto-assign → university accept / decline.

Runs against a throwaway SQLite database (never touches societal_ai.db ->
note it must be run STANDALONE so the temp-DB env var is honored).

  1. Register an institution (full capability profile)  POST /api/auth/register/common
  2. Register + login a citizen                         POST /api/auth/register/common, /api/auth/login
  3. Citizen reports a problem with an evidence photo   POST /api/problems
  4. Run AI analysis (auto-assigns top university)      POST /api/problems/<id>/analyze
  5. University sees the incoming challenge             GET  /api/university/incoming
  6. University accepts → project + milestones created  POST /api/university/challenges/<id>/accept
  7. Second problem declined with reason → re-routed    POST /api/university/challenges/<id>/decline
"""
import io
import os
import sys
import tempfile

# Must be set BEFORE any project module import so config points at a temp DB.
_TMP_DB = os.path.join(tempfile.mkdtemp(), "e2e_test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TMP_DB
os.environ["SOCIALAI_SKIP_WARMUP"] = "1"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from config import Config as _Cfg
if "e2e_test.db" not in _Cfg.DATABASE_URL:
    pytest.skip(
        "test_e2e_api_flow must run standalone (temp-DB env ignored because "
        f"config was already imported with DB {_Cfg.DATABASE_URL})"
    )

from app import create_app
from database.db import get_db

app = create_app()
client = app.test_client()

# 1x1 transparent PNG
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

_UNI_EMAIL = "e2e-university@example.edu"
_UNI_DEFAULT_PW = "e2e-university12345"
_CITIZEN_EMAIL = "e2e-citizen@example.com"
_CITIZEN_PW = "citizen-pass-123"


def _db_grab(query, params=()):
    with get_db() as db:
        row = db.execute(query, params).fetchone()
        return dict(row) if row else None


def test_full_university_citizen_assign_flow():
    # ---------------------------------------------------------------- 1. REGISTER UNIVERSITY
    r = client.post("/api/auth/register/common", json={
        "account_type": "institution",
        "name": "E2E Test University",
        "email": _UNI_EMAIL,
        "position": "Director",
        "institution": {
            "name": "E2E Test University of Applied Sciences",
            "institution_type": "university",
            "city": "Madurai", "state": "Tamil Nadu", "capacity": 25,
            "description": "Water, sanitation and public health engineering institution.",
            "website": "https://e2e.example.edu",
            "research_summary": "Focused on groundwater quality, sewage treatment and rural water supply.",
            "expertise_summary": "Civil engineering, hydrology, water quality analysis.",
            "programs_summary": "B.Tech Water Resources, M.Tech Environmental Engineering.",
            "facilities_summary": "Water testing lab with ICP-MS and microbiology lab.",
            "research_areas": [
                {"area": "Water quality", "keywords": "contamination, groundwater, arsenic"},
                {"area": "Sanitation", "keywords": "sewage, drainage, treatment"},
            ],
            "facilities": [
                {"name": "Water Testing Lab", "type": "laboratory",
                 "capabilities": "ICP-MS, titration, bacterial culture"},
            ],
            "programs": [
                {"name": "B.Tech Water Resources", "department": "Civil",
                 "focus": "hydrology, irrigation"},
            ],
            "faculty": [
                {"name": "Dr. A. Kumar", "department": "Civil",
                 "expertise": "hydrology, water quality"},
            ],
            "previous_projects": [
                {"title": "Arsenic removal pilot",
                 "description": "Community arsenic filter for 500 households"},
            ],
        },
    })
    assert r.status_code == 201, f"university register failed: {r.get_data(as_text=True)}"
    uni_user = r.get_json()["user"]
    org_id = uni_user["org_id"]

    uni_row = _db_grab("SELECT * FROM universities WHERE id=?", (org_id,))
    assert uni_row, "university row missing"
    assert uni_row["institution_type"] == "university"
    assert uni_row["verified"] == 0, "new institution should start unverified"
    for table in ("institution_research_areas", "institution_facilities",
                  "institution_programs", "faculty", "previous_projects"):
        with get_db() as db:
            n = db.execute(
                f"SELECT COUNT(*) c FROM {table} WHERE university_id=?", (org_id,)).fetchone()["c"]
        assert n > 0, f"{table} empty after registration"
    with get_db() as db:
        db.execute("UPDATE universities SET verified=1 WHERE id=?", (org_id,))

    # ---------------------------------------------------------------- 2. CITIZEN REGISTER + LOGIN
    r = client.post("/api/auth/register/common", json={
        "account_type": "person", "name": "E2E Citizen",
        "email": _CITIZEN_EMAIL, "password": _CITIZEN_PW, "location": "Madurai"})
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post("/api/auth/login", json={"email": _CITIZEN_EMAIL, "password": _CITIZEN_PW})
    assert r.status_code == 200, r.get_data(as_text=True)

    # ---------------------------------------------------------------- 3. REPORT PROBLEM + EVIDENCE
    r = client.post("/api/problems", data={
        "title": "Drinking water contamination in Madurai village",
        "description": ("Dozens of families near the borewell have no safe drinking "
                        "water and contamination reports continue to rise this month."),
        "address": "Anna Nagar, Madurai",
        "evidence": (io.BytesIO(_PNG), "evidence.png"),
    }, content_type="multipart/form-data")
    assert r.status_code == 201, f"report failed: {r.get_data(as_text=True)}"
    body = r.get_json()
    problem_id = body["problem_id"]
    assert body["validity"]["label"] == "VALID", body
    with get_db() as db:
        ev = db.execute("SELECT COUNT(*) c FROM evidence WHERE problem_id=?",
                        (problem_id,)).fetchone()["c"]
    assert ev == 1, f"expected 1 evidence row, got {ev}"

    # ---------------------------------------------------------------- 4. ANALYZE + AUTO-ASSIGN
    r = client.post(f"/api/problems/{problem_id}/analyze")
    assert r.status_code == 200, f"analyze failed: {r.get_data(as_text=True)[:500]}"
    result = r.get_json()
    assert result.get("matches"), "no university matches produced"
    assert result["classification"]["category"], "no category assigned"
    auto = result.get("auto_assignment") or {}
    assert auto.get("university_id"), f"auto-assignment failed: {result.get('auto_assignment_error')}"
    assert not result.get("auto_assignment_error"), result["auto_assignment_error"]

    # ---------------------------------------------------------------- 5. UNIVERSITY LOGIN + INCOMING
    r = client.post("/api/auth/login", json={"email": _UNI_EMAIL, "password": _UNI_DEFAULT_PW})
    assert r.status_code == 200, f"university login failed: {r.get_data(as_text=True)}"

    # Seed a pending assignment for OUR registered university (auto-assign may
    # have picked any verified university) so accept/decline is deterministic.
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO assignments(problem_id, assignee_type, assignee_id, "
            "created_by, status, notes) VALUES(?,?,?,NULL,'pending','Test assignment')",
            (problem_id, "university", org_id))
        our_assignment_id = cur.lastrowid

    r = client.get("/api/university/incoming")
    assert r.status_code == 200, r.get_data(as_text=True)
    incoming = r.get_json()["assignments"]
    ids = [a["assignment_id"] for a in incoming]
    assert our_assignment_id in ids, f"our assignment {our_assignment_id} not in incoming {ids}"

    # ---------------------------------------------------------------- 6. ACCEPT → PROJECT + MILESTONES
    r = client.post(f"/api/university/challenges/{our_assignment_id}/accept")
    assert r.status_code == 200, f"accept failed: {r.get_data(as_text=True)}"
    assert r.get_json()["status"] == "accepted"
    stat = _db_grab("SELECT status FROM problems WHERE id=?", (problem_id,))
    assert stat["status"] == "in_progress", f"problem should be in_progress, got {stat}"
    proj = _db_grab("SELECT id, status FROM projects WHERE problem_id=? AND assigned_to_id=?",
                    (problem_id, org_id))
    assert proj and proj["status"] == "in_progress", "project not created in_progress"
    with get_db() as db:
        n_ms = db.execute("SELECT COUNT(*) c FROM project_milestones WHERE project_id=?",
                          (proj["id"],)).fetchone()["c"]
    assert n_ms == 6, f"expected 6 seeded milestones, got {n_ms}"
    assign = _db_grab("SELECT status FROM assignments WHERE id=?", (our_assignment_id,))
    assert assign["status"] == "accepted", assign

    # ---------------------------------------------------------------- 7. DECLINE + RE-ROUTE
    r = client.post("/api/problems", data={
        "title": "Streetlights out along Highway road at night",
        "description": ("All streetlight poles along the Highway stretch have been dark for "
                        "two weeks, causing accidents and unsafe conditions for pedestrians."),
        "address": "Highway Road, Madurai",
    }, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_data(as_text=True)
    problem2 = r.get_json()["problem_id"]
    r = client.post(f"/api/problems/{problem2}/analyze")
    assert r.status_code == 200, r.get_data(as_text=True)
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO assignments(problem_id, assignee_type, assignee_id, "
            "created_by, status, notes) VALUES(?,?,?,NULL,'pending','Test decline assignment')",
            (problem2, "university", org_id))
        decl_assignment_id = cur.lastrowid

    r = client.post(f"/api/university/challenges/{decl_assignment_id}/decline",
                    json={"reason": "missing_expertise"})
    assert r.status_code == 200, f"decline failed: {r.get_data(as_text=True)}"
    assert r.get_json()["status"] == "rejected"

    stat2 = _db_grab("SELECT status FROM problems WHERE id=?", (problem2,))
    assert stat2["status"] == "pending_reassignment", f"got {stat2}"
    assign2 = _db_grab("SELECT status, decline_reason FROM assignments WHERE id=?",
                       (decl_assignment_id,))
    assert assign2["status"] == "rejected", assign2
    assert assign2["decline_reason"] == "missing_expertise", assign2
    with get_db() as db:
        adj = db.execute(
            "SELECT penalty_factor, sample_count FROM matcher_learning_adjustments "
            "WHERE university_id=?", (org_id,)).fetchone()
        assert adj, "learning adjustment not recorded"
        rerouted = db.execute(
            "SELECT problem_id FROM assignments WHERE problem_id=? AND status='pending' "
            "AND assignee_id != ?", (problem2, org_id)).fetchone()
    assert rerouted, "no re-route happened after decline"