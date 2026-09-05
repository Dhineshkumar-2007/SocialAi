"""Migration 007: Fix users table CHECK constraint to include faculty/student roles.

SQLite does not support ALTER TABLE to modify CHECK constraints, so this
migration recreates the users table with the updated constraint if needed.
"""
import sqlite3


def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def migrate(conn):
    cursor = conn.cursor()

    if not _table_exists(cursor, "users"):
        print("[007] Table 'users' does not exist; skipping constraint fix")
        return

    # Check if the old constraint is in place by trying to insert a test row
    # with faculty role. If it fails, we need to recreate the table.
    try:
        cursor.execute(
            "INSERT INTO users(email, password_hash, name, role) VALUES('test_facility_check@example.com', 'x', 'test', 'faculty')"
        )
        # If successful, delete the test row and skip migration
        cursor.execute("DELETE FROM users WHERE email='test_facility_check@example.com'")
        print("[007] CHECK constraint already allows faculty/student roles (skipping)")
        return
    except sqlite3.IntegrityError:
        print("[007] CHECK constraint does not allow faculty/student roles; recreating table")
        # Fall through to recreate

    # Recreate users table with updated CHECK constraint
    # 1. Create new table with correct constraint
    cursor.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('citizen','admin','university','industry','faculty','student')),
            org_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Copy existing data
    cursor.execute("""
        INSERT INTO users_new(id, email, password_hash, name, role, org_id, created_at)
        SELECT id, email, password_hash, name, role, org_id, created_at FROM users
    """)

    # 3. Drop old table
    cursor.execute("DROP TABLE users")

    # 4. Rename new table
    cursor.execute("ALTER TABLE users_new RENAME TO users")

    # 5. Recreate indexes
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    conn.commit()
    print("[007] Migration 007 completed: users table CHECK constraint updated")
