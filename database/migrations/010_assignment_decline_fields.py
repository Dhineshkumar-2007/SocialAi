"""
Migration 010: Add decline fields + index to assignments.
- decline_reason: stores the reason when university declines
- declined_by: references the university that declined
- index on status for fast pending/active queries
"""
def _cols(db, table):
    return {r[1] for r in db.execute('PRAGMA table_info(%s)' % table).fetchall()}

def _add(db, table, col, typ):
    if col not in _cols(db, table):
        db.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table, col, typ))

def migrate(db):
    _add(db, 'assignments', 'decline_reason', 'TEXT')
    _add(db, 'assignments', 'declined_by', 'INTEGER')
    _add(db, 'assignments', 'declined_at', 'TEXT')

    # Fast lookup index on status column (covers all dashboard queries)
    try:
        db.execute(
            'CREATE INDEX IF NOT EXISTS idx_assignments_status '
            'ON assignments(status)'
        )
    except Exception:
        pass

    db.commit()
