"""
Migration 002: Project Workspace, Citizen Verification & Adaptive Learning
Creates tables for milestone tracking, resolution feedback, and matcher learning adjustments.
Safe, idempotent migration with proper rollback support.
"""


def migrate(db):
    """Execute migration 002: workspace and learning tables."""

    # 1. Project Milestones & Execution Tracking
    db.execute("""
        CREATE TABLE IF NOT EXISTS project_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            stage TEXT CHECK(stage IN ('prototype', 'pilot', 'deployment', 'maintenance')) DEFAULT 'prototype',
            target_date TEXT,
            completed_at TEXT,
            status TEXT CHECK(status IN ('pending', 'in_progress', 'submitted', 'verified')) DEFAULT 'pending',
            evidence_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # 2. Citizen Resolution Feedback & Verification
    db.execute("""
        CREATE TABLE IF NOT EXISTS resolution_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            is_resolved INTEGER NOT NULL CHECK(is_resolved IN (0, 1)),
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            feedback_text TEXT,
            photo_evidence_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 3. Matcher Adaptive Learning Weights
    db.execute("""
        CREATE TABLE IF NOT EXISTS matcher_learning_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            category TEXT,
            skill_name TEXT,
            penalty_factor REAL DEFAULT 1.0,
            sample_count INTEGER DEFAULT 0,
            last_reason TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (university_id) REFERENCES universities(id)
        )
    """)

    # 4. Create indexes for performance
    db.execute("CREATE INDEX IF NOT EXISTS idx_milestones_project ON project_milestones(project_id, status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_feedback_problem ON resolution_feedback(problem_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_learning_university ON matcher_learning_adjustments(university_id, category)")

    print("[Migration 002] Created project_milestones, resolution_feedback, matcher_learning_adjustments tables")


def rollback(db):
    """Rollback migration 002 (for development/testing only)."""
    db.execute("DROP TABLE IF EXISTS project_milestones")
    db.execute("DROP TABLE IF EXISTS resolution_feedback")
    db.execute("DROP TABLE IF EXISTS matcher_learning_adjustments")
    print("[Migration 002] ✗ Rolled back workspace and learning tables")
