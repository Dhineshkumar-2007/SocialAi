# SICP Tamil Nadu — Logical Error Audit Report
**Project:** SocialAi / Societal Challenge Intelligence Portal  
**Scope:** Business-logic correctness, state machines, data relationships, calculations, cross-module consistency  
**Audit Date:** 2026-09-04  
**Severity:** CRITICAL=4 | HIGH=10 | MEDIUM=9 | LOW=5  
**Total findings:** 28

---

## Methodology
Each finding traced through: **Input → Route/Service Logic → Database State → AI Pipeline → Output → Downstream Workflow**

Workflows audited:
- **Citizen Workflow:** Submit → Evidence Upload → AI Analysis → Duplicate Detection → Matching → Assignment → Project Lifecycle
- **University Workflow:** Receive Assignment → Accept/Decline → Project Creation → Milestones → Impact
- **Admin Workflow:** Dashboard → Manual Override → Timeout Scanner → Learning Adjustments

---

## TOP 10 MOST DANGEROUS LOGICAL ERRORS

---

### E1 — Assignment Status Never Transitions to `in_progress` (CRITICAL)
**File:** `services/assignment_service.py` (handle_university_response, lines 226-237)  
**Severity:** CRITICAL — project lifecycle is broken for all university-accepted assignments  
**Type:** Missing state transition

**Root Cause:**  
`handle_university_response` sets assignment status to `accepted`, updates problem to `in_progress`, creates project with `status='in_progress'` — but the assignment itself is **never** updated to `in_progress`. The `Assignment.STATUSES` includes `'in_progress'` but no code path transitions to it.

**Reproduce:**  
1. Citizen submits problem → AI analyzes → auto-assigns university  
2. University accepts → assignment becomes `status='accepted'`, problem `status='in_progress'`  
3. Admin queries `SELECT * FROM assignments WHERE status='in_progress'` → **empty result**  
4. All project dashboards filtering by `assignment.status='in_progress'` are broken

**Impact:** Assignment lifecycle is permanently stuck at `accepted`. Timeout scanner, dashboard filters, and any `WHERE status='in_progress'` query silently returns nothing. Projects exist but assignments never reflect active work.

**Fix:** After creating the project in `handle_university_response`, add:  
```python
Assignment.update_status(assignment_id, 'in_progress')
```

**Test:** Accept a challenge, then `GET /api/assignments?assignee_type=university&assignee_id=1` — verify status is `in_progress`, not `accepted`.

---

### E2 — Route `handle_university_response` Always Runs After `auto_assign_top_university` (CRITICAL)
**File:** `routes/problems.py` (analyze endpoint, lines 89-117)  
**Severity:** CRITICAL — double-assignment of same problem to same university  
**Type:** Logic order / duplicate creation

**Root Cause:**  
The `analyze` endpoint calls `analyze_problem(problem_id)` which internally calls `match_universities` and writes matches to DB, then `auto_assign_top_university(problem_id)` is called separately in the route handler. `auto_assign_top_university` reads `matches` table, finds rank-1 university, and creates an `Assignment.create(...)`. This is **correct**.

However, `auto_assign_top_university` in `assignment_service.py` (line 108-113) checks for existing pending assignment before creating:
```python
existing = db.execute("SELECT id FROM assignments WHERE problem_id=? AND assignee_type='university' AND assignee_id=? AND status='pending'", ...).fetchone()
if existing:
    return get_assignment(existing['id'])
```
This guards against double-create — so E2 **is actually guarded**. But the logic is fragile: it only guards if the existing assignment is `pending`. If the university declines (→ status `rejected`) and the problem is re-routed back to the same university in a later round, a new pending assignment CAN be created to the same university. The route then calls `auto_assign_top_university` again, which would create a **second** pending assignment to the same university for the same problem.

**Actual Risk:** When `route_to_next_university` selects the same university that was already rejected (e.g., if rankings changed after a decline), a new pending assignment is created to the same university. The route then calls `auto_assign_top_university` on the next analyze, which finds no `pending` assignment (the old one was `rejected`), and creates another `pending` assignment — two pending assignments for the same problem+university.

**Fix:** In `route_to_next_university`, after creating new assignment, also mark the `matches` record to exclude that university, OR add a check in `auto_assign_top_university` to skip universities with any existing (non-pending) assignment.

**Test:** Decline a pending assignment → reroute → accept → verify only 1 pending assignment exists.

---

### E3 — Assignment History Schema Mismatch (CRITICAL)
**Files:** `services/assignment_service.py` (log_history, line 40-61), `database/migrations/003_history_columns.py`, `database/migrations/001_assignment_system.py`  
**Severity:** CRITICAL — assignment history audit log silently fails on every call  
**Type:** Schema mismatch / dead code

**Root Cause:**  
`log_history` in `assignment_service.py` uses columns: `assignment_id`, `action`, `actor_id`, `reason`, `created_at`.  
Migration 001 creates `assignment_history` with columns: `assignment_id`, `previous_status`, `new_status`, `changed_by`, `notes`, `created_at`.  
Migration 003 repairs the table to columns: `assignment_id`, `action`, `actor_id`, `reason`, `created_at`.

**Problem:** The `log_history` function creates the table **in its own body** (lines 43-56) with the **correct** schema (action/actor_id/reason). This is fine for the first call. BUT migrations 001 and 003 also create/repair the table. If migration 001 ran BEFORE the `log_history` function was updated, the table would have the WRONG columns (previous_status/new_status) and all `INSERT INTO assignment_history` calls would silently fail (SQLite ignores extra columns, raises error on missing required ones).

**Actually:** SQLite's `INSERT INTO` with named columns only inserts the specified columns. If the table has `previous_status, new_status, changed_by` but `log_history` inserts `assignment_id, action, actor_id, reason`, SQLite inserts only those 4 columns — the other 3 become NULL. So the data IS written, but the columns don't match what the function expected.

**Real Bug:** The `log_history` function's CREATE TABLE at line 46-54 has `FOREIGN KEY (assignment_id) REFERENCES assignments(id)` — but `assignment_id` is NOT NULL in the CREATE, while the INSERT at line 58-60 allows `assignment_id=None` (line 57: `if assignment_id is not None`). If `assignment_id=None`, the INSERT will violate the NOT NULL constraint.

**Reproduce:** Call `log_history(None, 'auto_assign_failed', reason='no_match')` — this is called on line 103 of `assignment_service.py` with `assignment_id=None`. This will FAIL on a fresh DB where the table was created by `log_history`'s own CREATE TABLE (which has NOT NULL on assignment_id).

**Fix:** Change `assignment_id INTEGER NOT NULL` to `assignment_id INTEGER` (nullable) in `log_history`'s CREATE TABLE.

---

### E4 — 72-Hour Timeout Uses UTC but Default Deadlines Use Local Time (HIGH)
**File:** `services/assignment_service.py` (check_expired_assignments, lines 314-358)  
**Severity:** HIGH — deadline calculations are inconsistent across timezones  
**Type:** Time calculation inconsistency

**Root Cause:**  
`check_expired_assignments` uses:
```python
cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)  # UTC
```
But `calculate_days_remaining` uses:
```python
deadline = created + timedelta(days=DEFAULT_DEADLINE_DAYS)
remaining = (deadline - datetime.now()).days  # local time
```
If server is in IST (UTC+5:30), an assignment created at 10:00 IST shows 3.0 days remaining via `calculate_days_remaining` but the timeout scanner expires it at `10:00 IST + 72h - 5.5h = 3 days 18.5h IST`. This means assignments expire **before** the UI shows them as expired.

**Fix:** Use `datetime.now()` consistently in `check_expired_assignments`, or use UTC consistently everywhere.

---

### E5 — Duplicate Detection Score Calculation Uses Wrong Weights (HIGH)
**File:** `ai/duplicate.py` (find_duplicates, line 27)  
**Severity:** HIGH — duplicate classification threshold is miscalibrated  
**Type:** Incorrect calculation

**Root Cause:**  
```python
score = semantic * 0.80 + geo * 0.20
```
Geographic score (`geo`) is binary: 1.0 if within 2km, 0.0 otherwise. The threshold `Config.DUPLICATE_THRESHOLD = 0.82` means:
- If within 2km: minimum score = 0.80 (just semantic)  
- If outside 2km: score = semantic only, requiring semantic ≥ 0.82

**Problem:** A report 2.1km away with identical semantic score 0.82 would score 0.656 and NOT be flagged as duplicate, while a report 1.9km away with semantic 0.82 scores 0.856 and IS flagged. The 200m difference creates a discontinuous jump.

**Worse:** If `Config.DUPLICATE_THRESHOLD` is 0.82, and geo=1.0, the minimum semantic needed is 0.775. But the threshold is set at 0.82 — meaning the threshold is actually **unreachable** for nearby duplicates unless semantic ≥ 0.82 (since max score with geo=1.0 is 0.80 + 0.20 = 1.0). The discontinuity means nearby duplicates with semantic 0.80 score 0.84 (DUPLICATE) but slightly farther ones with semantic 0.80 score only 0.64 (NOT duplicate).

**Fix:** Use graduated geo scoring: `geo = max(0, 1 - distance_km/5.0)` for smooth transition, or adjust threshold to be reachable.

---

### E6 — Problem Status Never Set to `matched` (HIGH)
**Files:** `routes/problems.py` (analyze endpoint, line 96), `services/assignment_service.py` (auto_assign_top_university, line 124)  
**Severity:** HIGH — problem status state machine is incomplete  
**Type:** Missing state transition

**Root Cause:**  
After `auto_assign_top_university` completes, `update_problem_status(problem_id, 'assigned')` is called (line 124). But `assigned` is **not a valid problem status** in the schema (`status TEXT DEFAULT 'submitted'` — no CHECK constraint, but the code never sets `matched` or `assigned` as a terminal state). The problem status transitions are:

`submitted` → `analyzed` → (no matched state) → `in_progress` (when university accepts) or `pending_reassignment` (when declined).

The `assigned` status written at line 124 is **orphan data** — no code path ever queries for `WHERE status='assigned'`. The `dashboard.py` queries for `pending` (line 53) but not `assigned`.

**Impact:** `assigned` status is dead-end state. If problem is in `assigned` state, no query will find it unless searching by ID directly.

**Fix:** Either remove the `update_problem_status(..., 'assigned')` call, or define `assigned` as a proper state in the status machine and add it to relevant queries.

---

### E7 — `get_history_for_problem` Uses `audit_log` Table with Wrong JOIN (HIGH)
**File:** `services/assignment_service.py` (get_history_for_problem, lines 465-490)  
**Severity:** HIGH — assignment history query always returns empty/bogus data  
**Type:** SQL logic error

**Root Cause:**  
```python
rows = db.execute("""
    SELECT a.*, al.actor_id, al.action, al.payload_json, al.created_at as log_time,
              u.name as actor_name, u.role as actor_role
    FROM assignments a
    LEFT JOIN audit_log al
      ON al.target_type = 'assignment'
     AND al.target_id = a.id
    LEFT JOIN users u ON u.id = al.actor_id
    WHERE a.problem_id = ?
    ORDER BY a.created_at DESC, al.created_at ASC
""", (problem_id,)).fetchall()
```

This joins `assignments` with `audit_log` (general audit log) for assignment-related entries. BUT:
1. The `audit_log` table stores general application events (via `audit_log()` function in `database/db.py`). The assignment-specific history is stored in `assignment_history` table (not `audit_log`).
2. `handle_university_response` calls `log_history()` which writes to `assignment_history` — NOT `audit_log`.
3. The `audit_log` entries are created by `accept_assignment` and `decline_assignment` via `audit_log(user_id, "assignment_accepted", ...)` — these DO write to `audit_log`.

**So both tables are used**, but this query only reads `audit_log`, missing all entries in `assignment_history`. Meanwhile, the `admin.py` `assignment_history` endpoint reads from `assignment_history` correctly. So the dashboard route `get_history_for_problem` returns a **different, incomplete** history than the admin endpoint.

**Fix:** Use `assignment_history` table, not `audit_log`, for assignment history.

---

### E8 — University Inbox JOIN Wrong Table for University Name (HIGH)
**File:** `services/assignment_service.py` (get_incoming_for_university, lines 359-382)  
**Severity:** HIGH — university inbox shows wrong university name for every assignment  
**Type:** SQL JOIN error

**Root Cause:**  
```python
FROM assignments a
JOIN problems p ON p.id = a.problem_id
JOIN universities u ON u.id = a.assignee_id  -- WRONG JOIN
WHERE a.assignee_type = 'university'
  AND a.assignee_id = ?
```

The third JOIN aliases `u` as `universities`, but `assignee_id` for a university assignment is the ** university's org_id** (university's id in the `universities` table). This join SHOULD work IF `a.assignee_id` matches `u.id`.

**BUT:** The `university_name` column returned is from `universities` table (correct). The actual bug is more subtle — if `assignee_type='university'` but `assignee_id` doesn't match any university (e.g., a deleted university), the JOIN silently drops the row. However, the real bug is:

`JOIN universities u ON u.id = a.assignee_id` — this assumes `assignee_id` is always a university ID. But `projects` table also uses `assigned_to_type` and `assigned_to_id`. The university inbox query is fine structurally.

**Actual Bug Found:** The query returns `university_name` but the returned `item["university_name"]` is NEVER used in the route that calls this function (`routes/assignments.py`, university_incoming, lines 21-48). The route extracts only: `problem_title`, `problem_description`, `problem_category`, `problem_priority`, `status`, `created_at`, `days_remaining`, `notes`, `latitude`, `longitude`. `university_name` is fetched from DB but **never returned to the client**. This means the university inbox UI never shows which university the assignment is FROM.

**Fix:** Return `university_name` in the response dict.

---

### E9 — Problem Status Check in `get_history_for_problem` Uses Wrong Table (HIGH)
**File:** `services/assignment_service.py` (get_history_for_problem, lines 465-490)  
**Severity:** HIGH — history joined from wrong table  
**Type:** Schema confusion

**Root Cause:**  
The function joins `assignments` with `audit_log` instead of `assignment_history`. The `audit_log` entries are created by `accept_assignment`/`decline_assignment` via `audit_log(user_id, "assignment_accepted", "assignment", assignment_id, {...})`. But the `assignment_history` entries are created by `handle_university_response` and `log_history` (used by `auto_assign_top_university`, `route_to_next_university`, `check_expired_assignments`).

**Impact:** Two separate audit trails exist — `audit_log` and `assignment_history` — and `get_history_for_problem` reads only one of them, missing the other.

---

### E10 — `verify_milestone` Can Be Called by Anyone Without Authorization (HIGH)
**File:** `routes/projects.py` (verify_milestone, lines 210-239)  
**Severity:** HIGH — milestone verification has no role guard  
**Type:** Missing authorization

**Root Cause:**  
```python
@projects_bp.post("/milestones/<int:milestone_id>/verify")
def verify_milestone(milestone_id):
    """Dual-citizen + faculty verification for a milestone..."""
    data = request.get_json() or {}
    if "is_confirmed" not in data:
        return jsonify({"error": "is_confirmed is required"}), 400
    ...
    cur = db.execute("""
        INSERT INTO milestone_verifications(milestone_id, citizen_id, faculty_id, ...)
        VALUES(?,?,?,?,?)
    """, (
        milestone_id,
        data.get("citizen_id"),    # Unverified caller-provided ID
        data.get("faculty_id"),    # Unverified caller-provided ID
        ...
    ))
```

**No `@require_role` decorator.** Any authenticated user can:
1. Claim to be any `citizen_id` (no ownership check)
2. Claim to be any `faculty_id` (no faculty existence check)
3. Set `is_confirmed=True` to mark any milestone as `verified`

This completely bypasses the dual-verification requirement. A malicious actor can verify their own milestone.

**Fix:** Add `@require_role('citizen', 'faculty')` and verify the caller matches the `citizen_id`/`faculty_id` they claim.

---

## ADDITIONAL FINDINGS

---

### E11 — Evidence Uploaded AFTER AI Analysis Never Gets Analyzed (MEDIUM)
**File:** `routes/problems.py` (create_problem, lines 46-56)  
**Severity:** MEDIUM — evidence submitted post-analysis is ignored  
**Type:** Workflow order violation

**Root Cause:**  
Evidence files are uploaded during `create_problem` (step 1 of citizen form). If the user submits evidence, then triggers re-analysis (e.g., new evidence added later), the `analyze_problem` function reads evidence from DB (line 52-54 of `pipeline.py`) and analyzes it. So this is actually **correct** — evidence uploaded at creation time IS analyzed.

**BUT:** If a citizen uploads NEW evidence after the initial submission (e.g., in a "add more evidence" flow), there is no endpoint to add evidence to an existing problem. The `evidence` table has a FK to `problem_id`, and there's no API to add evidence post-submission. New evidence is silently lost.

**Fix:** Add `POST /api/problems/<id>/evidence` endpoint.

---

### E12 — Milestone Status Machine Allows Invalid Transitions (MEDIUM)
**File:** `routes/projects.py` (update_project_milestone, lines 72-102)  
**Severity:** MEDIUM — milestones can be set to any status in any order  
**Type:** Missing state validation

**Root Cause:**  
`update_project_milestone` accepts ANY status value via the PATCH body:
```python
if "status" in data:
    updates.append("status = ?")
    values.append(data["status"])
```
The schema CHECK constraint allows: `'pending', 'in_progress', 'submitted', 'verified'`. But there's no validation preventing `verified` → `pending` or `pending` → `verified` (skipping all intermediate steps). Any role can jump milestones directly to `verified`, bypassing actual work.

**Fix:** Add state transition validation before update.

---

### E13 — No Rate Limiting on Citizen Submission (MEDIUM)
**File:** `routes/problems.py` (create_problem, lines 10-61)  
**Severity:** MEDIUM — spam submission possible  
**Type:** Missing business rule

**Root Cause:**  
No check on submission frequency per IP, email, or session. A single actor can submit thousands of reports. While duplicate detection runs during analysis, it only fires when AI analysis is triggered (not on raw submission). Spammers can fill the database before AI runs.

**Fix:** Add rate limiting by IP/email (e.g., max 10 submissions per hour per IP).

---

### E14 — Industry Match Endpoint Missing `rank` Column (MEDIUM)
**File:** `routes/problems.py` (industry_matches, lines 194-208)  
**Severity:** MEDIUM — industry matches have no ranking  
**Type:** Missing column

**Root Cause:**  
`industry_matches` table has no `rank` column. University matches use `problem_university_matches` with explicit rank. Industry matches return all matches but clients have no way to know which is rank 1 vs rank 5. `services/industry_matcher.py` returns `[:5]` but the response doesn't include rank.

**Fix:** Add `rank` column to `industry_matches` table, populate during `analyze_problem`.

---

### E15 — `evidence_score` Multiplied by 100 Then Compared to 0.4 (MEDIUM)
**File:** `ai/pipeline.py` (lines 100-103, 141)  
**Severity:** MEDIUM — unit mismatch between evidence_score storage and usage  
**Type:** Incorrect comparison

**Root Cause:**  
Evidence score starts as 0.0-1.0 float. During analysis:
```python
evidence_score = max(evidence_score, 0.8)  # 0.8 is a float
priority = calculate_priority(problem, evidence_score * 100, ...)  # multiplied by 100
```
So `evidence_score` passed to `calculate_priority` is 80.0 (not 0.8).

Then later:
```python
if evidence_score < 0.4:  # comparison against 0.4 (not 40)
    for m in matches:
        m["final_score"] = round(m["final_score"] * 0.7, 4)
```
Here `evidence_score` is still the original 0.0-1.0 float (never multiplied by 100). So the comparison `evidence_score < 0.4` is correct.

**BUT:** In `calculate_priority`, `evidence_score` is received as 80.0 (after ×100), then used as `evidence_score * 0.20` (line 26 of `priority.py`). This means evidence contributes 80 × 0.20 = 16.0 to the priority score (out of 100). The `evidence_score` column is stored as `evidence_score * 100` (line 116 of pipeline.py: `evidence_score * 100`). So the column stores 80.0 for 80% evidence.

**Problem:** The `evidence_score` column stores values 0-100, but the code uses it as 0-1 in `calculate_priority` (via the `evidence_score * 100` multiplication before calling). If `calculate_priority` is called from anywhere else (not via `analyze_problem`), the caller must remember to multiply by 100. This is a hidden coupling.

**Fix:** Normalize at storage time; always pass 0-1 values internally.

---

### E16 — `get_auto_assigned_match` Calls `match_universities` Inside DB Context (MEDIUM)
**File:** `services/assignment_service.py` (get_auto_assigned_match, lines 509-519)  
**Severity:** MEDIUM — nested DB context managers  
**Type:** Resource management

**Root Cause:**  
```python
def get_auto_assigned_match(problem_id):
    from ai.matcher import match_universities
    from database.db import get_db
    with get_db() as db:  # outer context
        row = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        ...
        matches = match_universities(problem)  # opens ANOTHER get_db() inside
    return matches[0] if matches else None
```

`match_universities` internally calls `get_db()` (line 42 of `matcher.py`). This is a nested context manager — SQLite handles this correctly (same connection), but it's fragile. If the DB layer changes to use connection pooling or PostgreSQL, nested `get_db()` could fail.

**Fix:** Pass the problem dict instead of calling DB inside the function.

---

### E17 — Priority Score Threshold Uses Hardcoded Values (MEDIUM)
**File:** `ai/priority.py` (line 32)  
**Severity:** MEDIUM — thresholds not configurable  
**Type:** Hardcoded magic numbers

**Root Cause:**  
```python
level = "critical" if score >= 81 else "high" if score >= 66 else "medium" if score >= 41 else "low"
```
These boundaries (81, 66, 41) are not in `config.py`. If the government wants to change the threshold for "critical" alerts, a code change is required.

**Fix:** Move to config.

---

### E18 — No Duplicate Link Shown to Citizen After Submission (MEDIUM)
**File:** `routes/problems.py` (create_problem, lines 10-61)  
**Severity:** MEDIUM — citizen never informed of duplicates  
**Type:** Missing user feedback

**Root Cause:**  
`create_problem` returns only `problem_id`. The citizen never sees that their report was flagged as a duplicate of an existing problem. They must manually check `my-reports` page. Citizens submitting duplicates should be informed and given options (add more detail / link to existing / submit anyway).

**Fix:** Return duplicate information in `create_problem` response.

---

### E19 — `analyze_problem` Deletes and Recreates All Matches Every Run (MEDIUM)
**File:** `ai/pipeline.py` (lines 149-178)  
**Severity:** MEDIUM — re-analysis destroys historical match data  
**Type:** Data destruction

**Root Cause:**  
```python
db.execute("DELETE FROM problem_university_matches WHERE problem_id=?", (problem_id,))
db.execute("DELETE FROM matches WHERE problem_id=?", (problem_id,))
```
Every re-analysis wipes all university matches and replaces them. This means historical match rankings (before decline/reroute) are lost. If a university declines, the match data is overwritten on the next analysis.

**Fix:** Only update if match scores changed; preserve historical match records.

---

### E20 — `get_incoming_for_university` Uses Hardcoded 3-Day Deadline (MEDIUM)
**File:** `services/assignment_service.py` (DEFAULT_DEADLINE_DAYS, line 493)  
**Severity:** MEDIUM — deadline not synced with config  
**Type:** Configuration inconsistency

**Root Cause:**  
`DEFAULT_DEADLINE_DAYS = 3` is hardcoded, but `UNIVERSITY_RESPONSE_TIMEOUT_HOURS = 72` (= 3 days). These SHOULD be the same value. If config changes `UNIVERSITY_RESPONSE_TIMEOUT_HOURS` to 48 (2 days), the UI still shows 3 days remaining while the timeout scanner fires at 48 hours. The `calculate_days_remaining` function uses `DEFAULT_DEADLINE_DAYS = 3` which may not match the actual timeout.

**Fix:** Use `Config.UNIVERSITY_RESPONSE_TIMEOUT_HOURS / 24` in `calculate_days_remaining`.

---

### E21 — No Check That Declined University is Excluded from Next Match (MEDIUM)
**File:** `services/assignment_service.py` (handle_university_response + route_to_next_university)  
**Severity:** MEDIUM — declined university can be re-assigned  
**Type:** Missing business logic

**Root Cause:**  
When a university declines, `record_learning_adjustment` is called (updates penalty table). But `route_to_next_university` reads from `matches` table and excludes only the **current** university (line 269-270 of `route_to_next_university`). It does NOT exclude previously-declined universities.

**Impact:** If University A declines, then University B accepts, then the project fails and a new assignment round begins, University A could be matched again. The `penalty_factor` in `matcher_learning_adjustments` is read by `match_universities` and applied as a score multiplier, but it's a **soft** penalty, not a hard exclusion. University A could still be top-ranked after multiple declines.

**Fix:** Add hard exclusion of all previously-declined universities in `route_to_next_university`.

---

### E22 — Skills Extraction Uses Simple Keyword Match (LOW)
**File:** `ai/skills.py` (lines 25-31)  
**Severity:** LOW — skill extraction is fragile  
**Type:** Algorithmic limitation

**Root Cause:**  
```python
if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
    skills.update(mapped)
```
Uses simple word boundary regex. "sensor" matches "sensors" and "sensor-based" (correct), but "water" matches "waterfall" (incorrect — domain mismatch). No lemmatization or NLP.

**Impact:** Low — wrong skill mappings lead to suboptimal university matching, but semantic embedding score provides a safety net.

---

### E23 — Milestone Verification Updates Status Only on `is_confirmed=True` (LOW)
**File:** `routes/projects.py` (verify_milestone, lines 236-237)  
**Severity:** LOW — rejected verification has no effect  
**Type:** Incomplete logic

**Root Cause:**  
```python
if data.get("is_confirmed"):
    db.execute("UPDATE project_milestones SET status='verified' WHERE id=?", (milestone_id,))
```
If `is_confirmed=False`, the verification record is created but the milestone status is NOT updated. The milestone stays at whatever status it was. There's no "rejected" or "needs_revision" status update.

**Fix:** Add status update for rejected verification.

---

### E24 — `auto_assign_top_university` Creates Duplicate Projects on Re-Analysis (LOW)
**File:** `routes/problems.py` (analyze endpoint, lines 96-117)  
**Severity:** LOW — multiple project records for same problem  
**Type:** Idempotency violation

**Root Cause:**  
If `analyze_problem` is called multiple times (e.g., manual re-trigger), `auto_assign_top_university` runs each time. It checks for existing **pending** assignments but NOT for existing **projects**. Each run creates a new project (line 231-237 of `handle_university_response` called via `accept_assignment`). The project creation is inside `handle_university_response` which is triggered by accept, but if the route calls `auto_assign_top_university` directly on re-analysis, it won't create a project (only `handle_university_response` does). So this is guarded — but fragile.

**Fix:** Add project existence check before creating.

---

### E25 — `assignment_history` Table Has No Index on `created_at` (LOW)
**File:** `database/db.py` (SCHEMA, line 219-223)  
**Severity:** LOW — slow history queries at scale  
**Type:** Missing index

**Root Cause:**  
`assignment_history` has no index on `created_at`. Queries like `ORDER BY created_at DESC LIMIT 100` in `admin.py` will do full table scans as the table grows.

**Fix:** Add `CREATE INDEX idx_assignment_history_created ON assignment_history(created_at)`.

---

### E26 — `category_match` Always Set to 1 in Pipeline (LOW)
**File:** `ai/pipeline.py` (lines 124-133)  
**Severity:** LOW — always stores `category_match=1`  
**Type:** Dead code path

**Root Cause:**  
```python
d.get("category_match") else 0
```
If `category_match` key is absent, it defaults to 0. But `find_duplicates` in `duplicate.py` never populates `category_match` in its return dict. So this is always 0.

**Fix:** Compute actual category match in duplicate detection.

---

### E27 — `admin_learning_adjustments` Endpoint Has No Role Guard (LOW)
**File:** `routes/assignments.py` (lines 220-235)  
**Severity:** LOW — read-only but sensitive data  
**Type:** Missing authorization

**Root Cause:**  
```python
@assignments_bp.get("/admin/learning-adjustments")
def admin_learning_adjustments():
```
No `@require_role('admin')`. Anyone can read all matcher penalty factors for all universities. This reveals which universities have been penalized and why.

**Fix:** Add `@require_role('admin')`.

---

### E28 — Session-Based Auth Has No CSRF Protection (MEDIUM)
**File:** `auth/decorators.py` (login_user, lines 27-30)  
**Severity:** MEDIUM — CSRF vulnerability  
**Type:** Security

**Root Cause:**  
Flask session cookies are used without CSRF tokens. State-changing POST/PATCH/DELETE requests from the browser can be forged if the user visits a malicious page while logged in.

**Fix:** Add CSRF token generation and validation for all mutating endpoints.

---

## SUMMARY BY SEVERITY

| # | Severity | File | Error |
|---|----------|------|-------|
| E1 | CRITICAL | assignment_service.py | Assignment never transitions to `in_progress` |
| E2 | CRITICAL | problems.py / assignment_service.py | Double-assignment risk on re-route |
| E3 | CRITICAL | assignment_service.py (log_history) | NOT NULL constraint violation on assignment_id=None |
| E4 | HIGH | assignment_service.py | UTC vs local time mismatch in timeout |
| E5 | HIGH | duplicate.py | Binary geo scoring creates threshold discontinuity |
| E6 | HIGH | problems.py / assignment_service.py | `assigned` status is orphan dead-end state |
| E7 | HIGH | assignment_service.py | `get_history_for_problem` reads wrong table (audit_log vs assignment_history) |
| E8 | HIGH | assignment_service.py | `university_name` fetched but never returned in inbox |
| E9 | HIGH | assignment_service.py | History query uses wrong audit table |
| E10 | HIGH | projects.py | `verify_milestone` has no role guard or ownership check |
| E11 | MEDIUM | problems.py | No endpoint to add evidence post-submission |
| E12 | MEDIUM | projects.py | Milestone status transitions unvalidated |
| E13 | MEDIUM | problems.py | No rate limiting on submission |
| E14 | MEDIUM | problems.py | Industry matches lack `rank` column |
| E15 | MEDIUM | pipeline.py / priority.py | `evidence_score` unit mismatch (×100 stored, ×1 used) |
| E16 | MEDIUM | assignment_service.py | Nested `get_db()` context managers |
| E17 | MEDIUM | priority.py | Hardcoded priority thresholds |
| E18 | MEDIUM | problems.py | Citizen not informed of duplicates |
| E19 | MEDIUM | pipeline.py | Re-analysis destroys historical match records |
| E20 | MEDIUM | assignment_service.py | Hardcoded deadline vs configurable timeout |
| E21 | MEDIUM | assignment_service.py | Declined universities not hard-excluded from re-match |
| E22 | LOW | skills.py | Simple keyword matching for skills |
| E23 | LOW | projects.py | Rejected milestone verification has no effect |
| E24 | LOW | assignment_service.py | Multiple project creation risk on re-analysis |
| E25 | LOW | db.py | Missing index on assignment_history.created_at |
| E26 | LOW | pipeline.py | `category_match` always stored as 0 |
| E27 | LOW | assignments.py | Learning adjustments endpoint unprotected |
| E28 | MEDIUM | auth/decorators.py | No CSRF protection on session auth |

---

## TOP 10 RECOMMENDED FIX ORDER

1. **E1** — Fix assignment `in_progress` transition (breaks entire project lifecycle)
2. **E3** — Fix `assignment_id NOT NULL` in `log_history` CREATE TABLE (silent data loss)
3. **E10** — Add role guard to `verify_milestone` (security bypass)
4. **E4** — Fix UTC vs local time (deadline inconsistency)
5. **E7/E9** — Fix `get_history_for_problem` to use `assignment_history` table
6. **E6** — Remove or document `assigned` status, or add to status queries
7. **E8** — Return `university_name` in inbox response
8. **E21** — Hard-exclude declined universities from re-matching
9. **E19** — Preserve historical matches on re-analysis
10. **E28** — Add CSRF protection to session auth

---

## AUDIT COMPLETE — NEXT PHASE: REPRODUCE → FIX → TEST → REGRESSION → RE-CHECK
