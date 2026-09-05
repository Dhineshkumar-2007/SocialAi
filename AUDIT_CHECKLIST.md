# FULL AUDIT RESULTS — Societal Challenge Intelligence Platform

## 1. UI/UX Weaknesses
- `index.html` basic form — no visual journey labels, no AI processing explanation
- No role-specific navigation (all roles see same nav)
- No progress state UI for lifecycle: PROPOSED → ... → COMPLETED
- No empty/loading/error states for AI analysis
- Evidence upload has no file preview or file type guidance
- No visual distinction between citizen report, AI analysis, matching, assignment

## 2. Broken Workflows
- `routes/routes.py` empty
- `routes/assignments.py` exists but not registered in `app.py` (wait, it's registered — yes in app.py)
- No `faculty` or `student` role in `users` CHECK — migration 004 may fix
- No automatic rerouting visual (only backend timeouts)

## 3. Backend/API Problems
- `routes/routes.py` empty (no central route index) — minor
- `routes/problems.py`: `latitude`/`longitude` stored but map input needed (PART 3)
- Evidence analysis uses `os.path.join("uploads", ...)` — relies on relative path working
- Pipeline loads all AI models every time? No, they load lazily. Need to verify.

## 4. Database Problems
- `users` CHECK excludes `faculty`, `student` — migration 004 should fix
- `projects` status CHECK only `proposed` — should expand to full lifecycle
- `assignment_history` missing from schema (check 003)
- `problem_university_matches` exists (new) and `matches` legacy — both maintained correctly
- `resolution_feedback` exists
- `project_assignments`, `milestone_verifications` need migration 004

## 5. Auth/Authorization
- Role-based access exists via `auth/decorators.py`
- Session cookie secure (HTTPOnly, SameSite=Lax)
- No `faculty` or `student` in `require_role` check — migration 004 needed

## 6. AI Pipeline Problems
- Embedding, classifier, vision models load lazily — OK
- Duplicate detection compares all other problems — may be slow as DB grows (no index on embedding_json for vector search; SQLite uses NumPy fallback)
- Evidence analysis uses vision model — expensive
- No timing/logging for pipeline stages
- Confidence from cosine similarity used directly (`evidence_score`) — user specifically said NOT to treat similarity as calibrated probability (PART 5)

## 7. AI Reliability Problems
- `evidence_score` computed as `max(confidence)` for evidence with status `supporting` or `uncertain` — still treats similarity/confidence as calibrated score
- No explicit `SUPPORTING` / `UNCERTAIN` / `IRRELEVANT` / `MANUAL REVIEW REQUIRED` states shown clearly
- No configurable thresholds for evidence relevance
- Evidence status `pending` default — needs clear display

## 8. Evidence Verification
- Evidence has `evidence_status` (pending, supporting, uncertain, irrelevant, error) — good
- But `confidence` stored and used as calibrated score — NOT scientifically calibrated
- `relevance`, `quality` columns exist but not clearly explained
- No explicit message showing: "The uploaded image does not appear to visually support the reported challenge."

## 9. University Matching
- Multi-factor: semantic 40% / skill 25% / lab 15% / project 10% / capacity 10% — good
- Adaptive learning via EMA (`new_penalty = 0.7*old + 0.3*incoming`) — exists
- `problem_university_matches` stores rank — exists
- No clear explanation of WHY in UI (only basic `explanation` JSON stored)

## 10. Industry Matching
- `routes/industry` missing — industry dashboard exists but industry routes/file missing?
- Check `services/industry_matcher.py`
- `routes/industry` or `routes/industry_partner` not registered in `app.py`

## 11. Project Lifecycle Problems
- Project status only `proposed` — no full lifecycle enforcement
- Milestones exist but no milestone verification endpoint exposed in UI (exists in routes but no template)
- No project state machine visualization

## 12. Dashboard Problems
- `admin_dashboard_simple.html` exists — basic stats + audit log + adjustments
- No progress charts/sparklines
- No impact measurement cards
- University workspace (`university_workspace.html`) exists but needs improvement
- `templates/university/dashboard.html` — basic
- Industry dashboard (`templates/industry/dashboard.html`) — basic or missing?

## 13. Empty/Loading/Error States
- No explicit loading state for AI analysis
- No empty state for incoming university challenges
- `admin_dashboard_simple.html` has empty-state patterns but no AI processing explanation

## 14. Performance Problems
- AI pipeline loads all stages regardless of evidence quality — vision model always called for every evidence file (expensive)
- Duplicate detection compares ALL other problems (O(N) per analysis) — no index filter by category
- Embedding generation for every request — no caching
- No timing/logging added yet

## 15. Security Problems
- `SECRET_KEY` default `dev-secret` — OK for demo but should be set
- `CORS_ORIGINS` default `*` — wide open for demo
- File uploads: `secure_filename` used — OK
- No input sanitization shown for `evidence_url` — OK
- No XSS protection explicitly shown (Flask default templates autoescape)
- No rate limiting
- No CSRF tokens (using session cookies — acceptable for this architecture)

## 16. Data Consistency
- `problem_university_matches` + `matches` both maintained — consistent
- `assignment_history` and `audit_log` both exist — good
- `resolution_feedback` linked to `problem_id`
- `impact_metrics` links to both `problem_id` and `project_id`

## 17. Responsive Design
- Basic responsive grid cards in `admin_dashboard_simple.html`
- `index.html` uses `form-grid` but no mobile-first design shown
- No responsive breakpoints in custom CSS

## 18. Accessibility
- No `aria-label` on buttons
- No `alt` text for map
- No keyboard navigation focus states
- No screen-reader friendly progress indicators

## 19. Demo-Flow Weaknesses
- User submits challenge → AI analysis → no clear explanation of results
- University accepts/declines → reroute backend works but no visual confirmation
- Project lifecycle not shown as journey
- Impact measurement disconnected from original citizen report

## 20. SIH Judge Perspective
- Needs clear visual journey from citizen → AI → matching → collaboration → deployment → impact
- AI must be explainable (NOT black box percentages)
- Every stage must reference same challenge/project record
- Must show real database records, not simulated state
- Must demonstrate complete end-to-end workflow with actual backend
