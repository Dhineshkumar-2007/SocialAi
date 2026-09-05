"""Truncate universities table (remove all sample/test data).

Keeps schema intact. Only runs the universities table by default.
Optional --with-assignments to also clear assignment and project records.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db


def truncate_universities(also_clear: bool = False):
    with get_db() as db:
        if also_clear:
            # Order matters because of foreign keys
            tables = ["project_milestones", "projects", "assignments", "faculty",
                      "labs", "previous_projects", "institution_research_areas",
                      "institution_facilities", "institution_programs", "universities"]
            for t in tables:
                try:
                    db.execute(f"DELETE FROM {t}")
                    print(f"  cleared {t}")
                except Exception as e:
                    print(f"  skipped {t}: {e}")
        else:
            count = db.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
            db.execute("DELETE FROM universities")
            print(f"Removed {count} universities. Registered institutions preserved via signup.")


if __name__ == "__main__":
    also = "--with-assignments" in sys.argv
    if also:
        confirm = input("This will also clear assignments and projects. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    truncate_universities(also_clear=also)
    print("Done.")
