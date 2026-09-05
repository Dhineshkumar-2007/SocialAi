def migrate(db):
    # Add new problem fields if missing
    try:
        db.execute("ALTER TABLE problems ADD COLUMN submitter_type TEXT DEFAULT 'individual'")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE problems ADD COLUMN district TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE problems ADD COLUMN reporter_name TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE problems ADD COLUMN reporter_email TEXT")
    except Exception:
        pass
