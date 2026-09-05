"""Migration 001: AI University Assignment & Automatic Re-Routing system.

Adds rank to problem_university_matches and creates assignments + audit tables
with safe execution and error handling.
"""
import sqlite3


# Name of the match table targeted by this migration.
# (The architectural spec refers to it as ``problem_university_matches``.)
TARGET_MATCH_TABLE = "problem_university_matches"


def _column_exists(cursor, table_name, column_name):
    """Return True if ``column_name`` exists on ``table_name``."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
    except sqlite3.OperationalError:
        return False
    rows = cursor.fetchall()
    for row in rows:
        # PRAGMA table_info returns rows with positional columns:
        # cid, name, type, notnull, dflt_value, pk
        if len(row) >= 2 and row[1] == column_name:
            return True
    return False


def _table_exists(cursor, table_name):
    """Return True if ``table_name`` exists in the database."""
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def migrate(conn):
    """Run migration 001 with safe execution semantics.

    - Skips column adds when the column already exists.
    - Skips table creation when the table already exists.
    - Surfaces only unexpected errors.
    """
    cursor = conn.cursor()

    # 1. ALTER TABLE problem_university_matches ADD COLUMN rank INTEGER
    #    The column is nullable so existing rows remain valid; the pipeline
    #    backfills rank on every re-run of analyze.
    if not _table_exists(cursor, TARGET_MATCH_TABLE):
        print(
            f"[001] Table '{TARGET_MATCH_TABLE}' does not exist yet; "
            "creating minimal table with required columns."
        )
        try:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TARGET_MATCH_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    university_id INTEGER NOT NULL,
                    semantic_score REAL,
                    skill_score REAL,
                    lab_score REAL,
                    project_score REAL,
                    capacity_score REAL,
                    final_score REAL,
                    explanation TEXT,
                    rank INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            print(f"[001] Created fallback table '{TARGET_MATCH_TABLE}'")
        except sqlite3.OperationalError as e:
            print(f"[001] Could not create fallback match table: {e}")

    if _table_exists(cursor, TARGET_MATCH_TABLE):
        if _column_exists(cursor, TARGET_MATCH_TABLE, "rank"):
            print(
                f"[001] Column 'rank' already exists on "
                f"{TARGET_MATCH_TABLE} (skipping)"
            )
        else:
            try:
                cursor.execute(
                    f"ALTER TABLE {TARGET_MATCH_TABLE} ADD COLUMN rank INTEGER"
                )
                print(
                    f"[001] Added 'rank' column to {TARGET_MATCH_TABLE}"
                )
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    print(
                        f"[001] Column 'rank' already exists on "
                        f"{TARGET_MATCH_TABLE} (caught on add, skipping)"
                    )
                else:
                    raise
    else:
        print(
            f"[001] Skipping rank addition; table {TARGET_MATCH_TABLE} "
            "still does not exist."
        )

    # 2. CREATE TABLE assignments
    # Mirrors the existing assignments table; the assignment system
    # needs an explicit, idempotent CREATE here so the migration is
    # self-contained even if the legacy schema is not run first.
    assignments_sql = """
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        assignee_type TEXT NOT NULL CHECK(assignee_type IN ('university','industry')),
        assignee_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending','accepted','rejected','in_progress','completed')),
        created_by INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (problem_id) REFERENCES problems(id)
    )
    """
    try:
        cursor.execute(assignments_sql)
        print("[001] Ensured table 'assignments' exists")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg:
            print("[001] Table 'assignments' already exists (skipping)")
        else:
            raise

    # Indexes for assignments lookups.
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_assignments_problem ON assignments(problem_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_assignee ON assignments(assignee_type, assignee_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status)",
    ]:
        try:
            cursor.execute(idx_sql)
        except sqlite3.OperationalError as e:
            print(f"[001] Index create skipped: {e}")

    # 3. CREATE TABLE assignment_history (audit log)
    # One row per status change; provides full audit trail for re-routing
    # and admin actions.
    assignment_history_sql = """
    CREATE TABLE IF NOT EXISTS assignment_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        previous_status TEXT,
        new_status TEXT,
        changed_by INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assignment_id) REFERENCES assignments(id)
    )
    """
    try:
        cursor.execute(assignment_history_sql)
        print("[001] Ensured table 'assignment_history' exists")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg:
            print("[001] Table 'assignment_history' already exists (skipping)")
        else:
            raise

    # Back-populate ranks from existing `matches` rows into
    # `problem_university_matches` so historical data is ranked.
    # Rows are ordered by final_score DESC within each problem,
    # giving rank 1 to the best match.
    if _table_exists(cursor, "matches") and _table_exists(cursor, TARGET_MATCH_TABLE):
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO problem_university_matches
                    (problem_id, university_id, semantic_score, skill_score,
                     lab_score, project_score, capacity_score, final_score,
                     explanation, rank)
                SELECT
                    m.problem_id, m.university_id, m.semantic_score, m.skill_score,
                    m.lab_score, m.project_score, m.capacity_score, m.final_score,
                    m.explanation,
                    (
                        SELECT COUNT(*) + 1
                        FROM matches m2
                        WHERE m2.problem_id = m.problem_id
                          AND m2.final_score > m.final_score
                    ) AS rank
                FROM matches m
            """)
            print("[001] Back-populated ranks from legacy matches table")
        except sqlite3.OperationalError as e:
            print(f"[001] Rank backfill skipped: {e}")

    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assignment_history_assignment "
            "ON assignment_history(assignment_id)"
        )
    except sqlite3.OperationalError as e:
        print(f"[001] Index on assignment_history skipped: {e}")

    conn.commit()
    print("[001] Migration 001 completed successfully.")
