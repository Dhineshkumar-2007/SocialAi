"""
Migration 009: Add address column to problems table.
Replaces the removed latitude/longitude columns with a plain-text address field.
"""
def _cols(db, table):
    return {r[1] for r in db.execute('PRAGMA table_info(%s)' % table).fetchall()}

def _add(db, table, col, typ):
    if col not in _cols(db, table):
        db.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table, col, typ))

def migrate(db):
    _add(db, 'problems', 'address', 'TEXT')
    # Drop the old lat/long columns if they exist (SQLite supports rename only via recreate,
    # so we leave them in place — the application code simply ignores them)
    db.commit()
