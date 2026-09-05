"""Migration 008: Admin university verification workflow.
Adds promotion endpoint and uses existing `verified` column.
New universities register with verified=0; admin must set verified=1.
"""

def migrate(conn):
    cursor = conn.cursor()
    # Verify column exists (should already be present from prior schema)
    cursor.execute("SELECT 1 FROM pragma_table_info('universities') WHERE name='verified'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE universities ADD COLUMN verified INTEGER DEFAULT 0")
        conn.commit()
        print("[008] Added verified column")
    else:
        print("[008] Verified column present (existing schema)")
    # Set all existing universities to verified=1 (backward compat)
    cursor.execute("UPDATE universities SET verified = 1 WHERE verified IS NULL OR verified = 0")
    conn.commit()
    print("[008] Migration completed: admin verification workflow active")
