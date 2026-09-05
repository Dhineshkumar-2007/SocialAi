"""Precompute and persist embeddings for universities and industry partners.

Run once (or after data changes) so runtime matching reads stored embeddings
instead of re-encoding text on every AI analysis request:

    python scripts/backfill_embeddings.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.embeddings import generate_embedding
from ai.matcher import _g  # shared column access helper
from database.db import get_db


def main():
    with get_db() as db:
        unis = db.execute("SELECT * FROM universities WHERE verified=1").fetchall()
        faculty = db.execute("SELECT university_id, expertise FROM faculty").fetchall()
        labs = db.execute("SELECT university_id, facilities FROM labs").fetchall()
        projects = db.execute("SELECT university_id, description FROM previous_projects").fetchall()
        research = db.execute("SELECT university_id, area, keywords FROM institution_research_areas").fetchall()
        facilities = db.execute("SELECT university_id, name, type, capabilities FROM institution_facilities").fetchall()
        programs = db.execute("SELECT university_id, name, department, focus FROM institution_programs").fetchall()

        rows = {
            "faculty": faculty, "labs": labs, "projects": projects,
            "research": research, "facilities": facilities, "programs": programs,
        }

        # Build the exact same capability text the matcher uses.
        def build(uni):
            uid = uni["id"]
            part = {}
            for key, all_rows in rows.items():
                part[key] = [r for r in all_rows if r["university_id"] == uid]
            faculty_text = " ".join(_g(x, "expertise") for x in part["faculty"])
            lab_text = " ".join(_g(x, "facilities") for x in part["labs"])
            project_text = " ".join(_g(x, "description") for x in part["projects"])
            research_text = " ".join(f"{_g(x,'area')} {_g(x,'keywords')}" for x in part["research"])
            facility_text = " ".join(f"{_g(x,'name')} {_g(x,'type')} {_g(x,'capabilities')}" for x in part["facilities"])
            program_text = " ".join(f"{_g(x,'name')} {_g(x,'department')} {_g(x,'focus')}" for x in part["programs"])
            return (
                f"{_g(uni,'description')} {_g(uni,'expertise_summary')} "
                f"{_g(uni,'research_summary')} {_g(uni,'programs_summary')} "
                f"{_g(uni,'facilities_summary')} {research_text} {program_text} "
                f"{facility_text} {faculty_text} {lab_text} {project_text}"
            )

        texts = [(u["id"], u["name"], build(u)) for u in unis]
        emb = generate_embedding([t for _, _, t in texts])  # batched, single pass
        for (uid, name, _), e in zip(texts, emb):
            db.execute(
                "UPDATE universities SET embedding_json=? WHERE id=?",
                (json.dumps(e), uid))
        print(f"Universities: backfilled {len(texts)}")

        partners = db.execute("SELECT * FROM industry_partners").fetchall()
        ptexts = [(p["id"], f"{p['name']} {p['sector']} {p['capabilities_text']}") for p in partners]
        pemb = generate_embedding([t for _, t in ptexts])
        for (pid, _), e in zip(ptexts, pemb):
            db.execute(
                "UPDATE industry_partners SET embedding_json=? WHERE id=?",
                (json.dumps(e), pid))
        print(f"Industry partners: backfilled {len(ptexts)}")


if __name__ == "__main__":
    main()