"""Migration 006: Add assigned_to_type and assigned_to_id to projects table.

These columns are referenced by services/assignment_service.py create_project()
but were missing from the actual database table.
"""


def migrate(db):
    """Add assignment tracking columns to projects table."""

    # Check if columns already exist
    cols = [row[1] for row in db.execute('PRAGMA table_info(projects)').fetchall()]

    if 'assigned_to_type' not in cols:
        db.execute('ALTER TABLE projects ADD COLUMN assigned_to_type TEXT')
        print('[006] Added assigned_to_type to projects')

    if 'assigned_to_id' not in cols:
        db.execute('ALTER TABLE projects ADD COLUMN assigned_to_id INTEGER')
        print('[006] Added assigned_to_id to projects')

    if 'started_at' not in cols:
        db.execute('ALTER TABLE projects ADD COLUMN started_at TEXT')
        print('[006] Added started_at to projects')

    if 'completed_at' not in cols:
        db.execute('ALTER TABLE projects ADD COLUMN completed_at TEXT')
        print('[006] Added completed_at to projects')


def rollback(db):
    """Rollback not supported for ALTER TABLE ADD COLUMN in SQLite."""
    print('[006] Rollback not supported — column removal requires table rebuild')
