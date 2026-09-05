"""Migration 003: Repair assignment_history table.

The early CREATE TABLE in services/assignment_service.py was missing
several columns used by the audit log. This migration idempotently
adds them on startup.
"""
import sqlite3


def _column_exists(db, table, column):
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def migrate(db):
    # The table was created lazily; if it's still missing, create it fully.
    db.execute("""
        CREATE TABLE IF NOT EXISTS assignment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            action TEXT,
            actor_id INTEGER,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Now patch any missing columns.
    additions = [
        ("assignment_id", "INTEGER"),
        ("action",        "TEXT"),
        ("actor_id",      "INTEGER"),
        ("reason",        "TEXT"),
        ("created_at",    "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]
    for col, decl in additions:
        if not _column_exists(db, "assignment_history", col):
            try:
                db.execute(f"ALTER TABLE assignment_history ADD COLUMN {col} {decl}")
            except Exception:
                pass
