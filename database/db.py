import os
import sqlite3
import json
from contextlib import contextmanager
from config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 description TEXT NOT NULL,
 category TEXT,
 subcategory TEXT,
 latitude REAL,
 longitude REAL,
 status TEXT DEFAULT 'submitted',
 priority_score REAL DEFAULT 0,
 priority_level TEXT DEFAULT 'medium',
 evidence_score REAL DEFAULT 0,
 evidence_caption TEXT,
 skills_json TEXT DEFAULT '[]',
 embedding_json TEXT,
 created_by INTEGER,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER NOT NULL,
 filename TEXT NOT NULL,
 mime TEXT,
 caption TEXT,
 supports_report INTEGER DEFAULT 0,
 confidence REAL DEFAULT 0,
 evidence_status TEXT DEFAULT 'pending',
 relevance REAL DEFAULT 0,
 quality REAL DEFAULT 0,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS universities (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 city TEXT,
 description TEXT,
 capacity INTEGER DEFAULT 10,
 embedding_json TEXT,
 verified INTEGER DEFAULT 0,
 contact_email TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faculty (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 university_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 department TEXT,
 expertise TEXT,
 FOREIGN KEY (university_id) REFERENCES universities(id)
);

CREATE TABLE IF NOT EXISTS labs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 university_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 facilities TEXT,
 FOREIGN KEY (university_id) REFERENCES universities(id)
);

CREATE TABLE IF NOT EXISTS previous_projects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 university_id INTEGER NOT NULL,
 title TEXT NOT NULL,
 description TEXT,
 FOREIGN KEY (university_id) REFERENCES universities(id)
);

CREATE TABLE IF NOT EXISTS matches (
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
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id),
 FOREIGN KEY (university_id) REFERENCES universities(id)
);

CREATE TABLE IF NOT EXISTS problem_links (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER NOT NULL,
 similar_problem_id INTEGER NOT NULL,
 similarity REAL,
 distance_km REAL,
 category_match INTEGER DEFAULT 0,
 FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS projects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 status TEXT DEFAULT 'proposed',
 progress INTEGER DEFAULT 0,
 milestones_json TEXT DEFAULT '[]',
 impact_json TEXT DEFAULT '{}',
 assigned_to_type TEXT,
 assigned_to_id INTEGER,
 started_at TEXT,
 completed_at TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('citizen','admin','university','industry')),
 org_id INTEGER,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT UNIQUE NOT NULL,
 parent_id INTEGER,
 description TEXT,
 embedding_json TEXT
);

CREATE TABLE IF NOT EXISTS skills_taxonomy (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT UNIQUE NOT NULL,
 description TEXT,
 embedding_json TEXT
);

CREATE TABLE IF NOT EXISTS industry_partners (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 sector TEXT,
 region TEXT,
 capabilities_text TEXT,
 embedding_json TEXT,
 contact_email TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS industry_matches (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER NOT NULL,
 industry_id INTEGER NOT NULL,
 semantic_score REAL,
 skill_score REAL,
 sector_score REAL,
 final_score REAL,
 explanation TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id),
 FOREIGN KEY (industry_id) REFERENCES industry_partners(id)
);

CREATE TABLE IF NOT EXISTS assignments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER NOT NULL,
 assignee_type TEXT NOT NULL CHECK(assignee_type IN ('university','industry')),
 assignee_id INTEGER NOT NULL,
 status TEXT DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','in_progress','completed')),
 created_by INTEGER,
 notes TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 type TEXT NOT NULL,
 payload_json TEXT DEFAULT '{}',
 read_at TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS impact_metrics (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 problem_id INTEGER,
 project_id INTEGER,
 metric_key TEXT NOT NULL,
 metric_value REAL,
 recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (problem_id) REFERENCES problems(id),
 FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 actor_id INTEGER,
 action TEXT NOT NULL,
 target_type TEXT,
 target_id INTEGER,
 payload_json TEXT DEFAULT '{}',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status);
CREATE INDEX IF NOT EXISTS idx_problems_category ON problems(category);
CREATE INDEX IF NOT EXISTS idx_problems_priority ON problems(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_assignments_assignee ON assignments(assignee_type, assignee_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, read_at);
"""


def _sqlite_path():
    url = Config.DATABASE_URL
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return "societal_ai.db"


@contextmanager
def get_db():
    if Config.DATABASE_URL.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path())
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        import psycopg2
        conn = psycopg2.connect(Config.DATABASE_URL)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    # Always establish the base schema before migrations.
    try:
        with get_db() as db:
            db.executescript(SCHEMA)
    except Exception as exc:
        print(f"[schema] Base schema initialization error: {exc}")
        raise
    # Run assignment-system schema migration (safe / idempotent)
    try:
        import importlib
        migration_001 = importlib.import_module("database.migrations.001_assignment_system")
        with get_db() as db:
            migration_001.migrate(db)
    except Exception as exc:
        import traceback
        print(f"[migrate] Migration 001 error: {exc}")

    try:
        migration_005 = importlib.import_module("database.migrations.005_identity_and_institution_profiles")
        with get_db() as db:
            migration_005.migrate(db)
    except Exception as exc:
        import traceback
        print(f"[migrate] Migration 005 error: {exc}")
        traceback.print_exc()

    # Run workspace and learning migration (safe / idempotent)
    try:
        import importlib
        migration_002 = importlib.import_module("database.migrations.002_workspace_and_learning")
        with get_db() as db:
            migration_002.migrate(db)
    except Exception as exc:
        import traceback
        print(f"[migrate] Migration 002 error: {exc}")
        traceback.print_exc()

    # Repair assignment_history columns (idempotent ALTERs)
    try:
        import importlib
        migration_003 = importlib.import_module("database.migrations.003_history_columns")
        with get_db() as db:
            migration_003.migrate(db)
    except Exception as exc:
        import traceback
        print(f"[migrate] Migration 003 error: {exc}")
        traceback.print_exc()

    # Phase 2: role expansion + project assignments + milestone verification
    try:
        import importlib
        migration_004 = importlib.import_module("database.migrations.004_role_assignment_verification")
        with get_db() as db:
            migration_004.migrate(db)
    except Exception as exc:
        import traceback
        print(f"[migrate] Migration 004 error: {exc}")
        traceback.print_exc()
    with get_db() as db:
        if Config.DATABASE_URL.startswith("sqlite"):
            for statement in SCHEMA.split(";"):
                stripped = statement.strip()
                if stripped:
                    try:
                        db.execute(stripped)
                    except sqlite3.OperationalError as e:
                        if "already exists" not in str(e):
                            raise
            # Fix: add missing columns to existing tables
            for stmt in [
                "ALTER TABLE problems ADD COLUMN created_by INTEGER",
                "ALTER TABLE problem_links ADD COLUMN category_match INTEGER DEFAULT 0",
                "ALTER TABLE matches ADD COLUMN explanation TEXT DEFAULT '[]'",
                "ALTER TABLE problems ADD COLUMN address TEXT",
                "ALTER TABLE assignments ADD COLUMN decline_reason TEXT",
                "ALTER TABLE assignments ADD COLUMN declined_by INTEGER",
                "ALTER TABLE assignments ADD COLUMN declined_at TEXT",
            ]:
                try:
                    db.execute(stmt)
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                        raise
        else:
            cur = db.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    seed_categories()
    seed_skills_taxonomy()
    seed_universities()
    seed_industry_partners()
    seed_default_admin()


def seed_categories():
    """Seed problem category taxonomy."""
    categories = [
        ("Water and sanitation", None, "Water supply, drainage, sewage, sanitation issues"),
        ("Healthcare", None, "Medical facilities, health services, disease outbreaks"),
        ("Agriculture", None, "Farming, irrigation, crop issues, livestock"),
        ("Education", None, "Schools, literacy, educational infrastructure"),
        ("Environment", None, "Pollution, deforestation, climate, wildlife"),
        ("Infrastructure", None, "Roads, bridges, buildings, public works"),
        ("Waste management", None, "Garbage collection, disposal, recycling"),
        ("Energy", None, "Electricity, power supply, renewable energy"),
        ("Transportation", None, "Roads, public transport, traffic management"),
        ("Employment", None, "Jobs, vocational training, skill development"),
    ]
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if existing:
            return
        for name, parent, desc in categories:
            db.execute(
                "INSERT OR IGNORE INTO categories(name, parent_id, description) VALUES(?,?,?)",
                (name, parent, desc)
            )


def seed_skills_taxonomy():
    """Seed skills taxonomy for extraction."""
    skills = [
        ("Water Quality Analysis", "Testing and analyzing water samples for contamination"),
        ("Hydrology", "Study of water movement and distribution"),
        ("Environmental Engineering", "Engineering solutions for environmental problems"),
        ("IoT", "Internet of Things, sensor networks, embedded systems"),
        ("Sensor Networks", "Distributed sensor deployment and data collection"),
        ("Embedded Systems", "Microcontroller and firmware development"),
        ("Machine Learning", "ML algorithms, model training, data science"),
        ("Data Science", "Statistical analysis and data-driven insights"),
        ("GIS", "Geographic Information Systems, mapping, spatial analysis"),
        ("Geospatial Analysis", "Analysis of geographically referenced data"),
        ("Remote Sensing", "Satellite and aerial imagery analysis"),
        ("Agricultural Engineering", "Engineering for farming and agricultural systems"),
        ("Agriculture", "Farming techniques and crop management"),
        ("Civil Engineering", "Construction, structural, and infrastructure engineering"),
        ("Structural Engineering", "Design of load-bearing structures"),
        ("Waste Management", "Solid waste collection, treatment, recycling"),
        ("Healthcare", "Medical services and health infrastructure"),
        ("Health Informatics", "IT systems for healthcare management"),
        ("Education Technology", "Technology-enhanced learning solutions"),
        ("Transportation", "Transport systems and traffic engineering"),
        ("Traffic Engineering", "Traffic flow optimization and management"),
        ("Disaster Management", "Emergency response and disaster preparedness"),
        ("Climate Analytics", "Analysis of climate data and trends"),
    ]
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) FROM skills_taxonomy").fetchone()[0]
        if existing:
            return
        for name, desc in skills:
            db.execute(
                "INSERT OR IGNORE INTO skills_taxonomy(name, description) VALUES(?,?)",
                (name, desc)
            )


def seed_universities():
    """Seed top-tier Tamil Nadu universities with real faculty, labs, and projects."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

    try:
        from scripts.seed_top_universities import populate_top_universities
        populate_top_universities()
    except Exception as e:
        print(f"[seed_universities] Failed to load real university data: {e}")
        print("[seed_universities] Falling back to minimal seed")

        with get_db() as db:
            count = db.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
            if count:
                return

            # Minimal fallback seed
            universities = [
                ("Indian Institute of Technology Madras", "Chennai",
                 "Premier institute with AI, water tech, and cyber-physical systems research.", 15),
                ("National Institute of Technology Tiruchirappalli", "Tiruchirappalli",
                 "National institute with smart manufacturing, clean water, and renewable energy expertise.", 12),
            ]

            for u in universities:
                if Config.DATABASE_URL.startswith("sqlite"):
                    cur = db.execute(
                        "INSERT INTO universities(name,city,description,capacity,verified) VALUES(?,?,?,?,1)",
                        u
                    )
                else:
                    cur = db.cursor()
                    cur.execute(
                        "INSERT INTO universities(name,city,description,capacity,verified) VALUES(%s,%s,%s,%s,1) RETURNING id",
                        u
                    )


def seed_industry_partners():
    """Seed sample industry partners for CSR/technical collaboration."""
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM industry_partners").fetchone()[0]
        if count:
            return

        partners = [
            ("Tata Motors", "Automotive", "Tamil Nadu",
             "EV technology, rural mobility, IoT sensors, environmental monitoring, CSR infrastructure projects"),
            ("ITC Limited", "Agribusiness", "Pan India",
             "Agricultural supply chain, rural development, water management, sustainable farming"),
            ("Infosys Foundation", "IT Services", "Pan India",
             "Digital literacy, education technology, smart village initiatives, healthcare IT"),
            ("L&T Construction", "Infrastructure", "Pan India",
             "Roads, bridges, water supply systems, sewage treatment, disaster-resilient infrastructure"),
            ("Tamil Nadu Water Supply", "Government Utility", "Tamil Nadu",
             "Urban and rural water supply, sewage treatment, pipeline infrastructure, water quality"),
        ]

        for name, sector, region, capabilities in partners:
            db.execute(
                "INSERT INTO industry_partners(name, sector, region, capabilities_text) VALUES(?,?,?,?)",
                (name, sector, region, capabilities)
            )


def seed_default_admin():
    """Create default admin user if none exists."""
    from auth.models import hash_password, User
    with get_db() as db:
        admin = db.execute("SELECT * FROM users WHERE role='admin' LIMIT 1").fetchone()
        if admin:
            return
    # Create admin with default password
    User.create(
        email="admin@societali.ai",
        password="admin123",
        name="System Admin",
        role="admin"
    )


def audit_log(actor_id, action, target_type=None, target_id=None, payload=None):
    """Record an audit entry."""
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_log(actor_id, action, target_type, target_id, payload_json) VALUES(?,?,?,?,?)",
            (actor_id, action, target_type, target_id, json.dumps(payload or {}))
        )
