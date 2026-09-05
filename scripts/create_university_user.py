"""
Bootstrap helper: create a 'university' user account linked to a registered
university (org_id). Run this from the project root after `init_db()` has
seeded the universities table.

Usage:
    python scripts/create_university_user.py <email> <password> <name> [university_id]

If `university_id` is omitted, the script will:
  1. List all universities with their IDs and names.
  2. Try to match the email domain (e.g. iitm.ac.in -> "IIT Madras" in the seed data).
  3. Otherwise prompt for an ID interactively (skipped if --auto is set).

Examples:
    # Interactive — script will prompt for university ID:
    python scripts/create_university_user.py registrar@iitm.ac.in changeme "Registrar"

    # Non-interactive — explicit university ID:
    python scripts/create_university_user.py registrar@iitm.ac.in changeme "Registrar" 1
"""
import sys
import os
import argparse
import re

# Make the project root importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db
from auth.models import User


def list_universities():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, city, contact_email FROM universities ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def guess_university_id(universities, email):
    """Best-effort heuristic: match email domain to a university's city or name."""
    if not email or "@" not in email:
        return None
    domain = email.split("@", 1)[1].lower()
    # Strip common TLDs and look for a substring match in name/city.
    base = re.sub(r"\.(ac|edu|org|com|co|gov|in|uk)$", "", domain)
    for u in universities:
        haystack = (u["name"] + " " + (u.get("city") or "")).lower()
        for token in re.split(r"[\s.]+", haystack):
            if token and token in base:
                return u["id"]
    return None


def main():
    p = argparse.ArgumentParser(description="Create a university user account.")
    p.add_argument("email")
    p.add_argument("password")
    p.add_argument("name")
    p.add_argument("university_id", type=int, nargs="?", default=None,
                   help="Numeric universities.id; prompted if omitted.")
    p.add_argument("--auto", action="store_true",
                   help="Use heuristic match; if no match, abort without prompting.")
    args = p.parse_args()

    universities = list_universities()
    if not universities:
        print("ERROR: No universities in the database. Run `init_db()` first.", file=sys.stderr)
        sys.exit(1)

    uni_id = args.university_id
    if uni_id is None:
        uni_id = guess_university_id(universities, args.email)
        if uni_id is None:
            if args.auto:
                print("ERROR: No university matches email domain. Pass an explicit ID.", file=sys.stderr)
                sys.exit(2)
            print("Available universities:")
            for u in universities:
                print(f"  {u['id']:>3}  {u['name']}  ({u.get('city') or '-'})")
            try:
                raw = input("Enter university ID: ").strip()
                uni_id = int(raw)
            except (ValueError, EOFError):
                print("Aborted.", file=sys.stderr)
                sys.exit(3)

    # Validate the chosen ID.
    match = next((u for u in universities if u["id"] == uni_id), None)
    if not match:
        print(f"ERROR: University id={uni_id} not found.", file=sys.stderr)
        sys.exit(4)

    # Refuse if the email is already taken.
    if User.get_by_email(args.email):
        print(f"ERROR: A user with email {args.email} already exists.", file=sys.stderr)
        sys.exit(5)

    user = User.create(
        email=args.email,
        password=args.password,
        name=args.name,
        role="university",
        org_id=uni_id,
    )
    print(f"Created university user: id={user.id} email={user.email} "
          f"role={user.role} org_id={user.org_id} -> {match['name']}")


if __name__ == "__main__":
    main()
