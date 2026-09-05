"""Assignment model for admin assigning problems to university/industry."""
from database.db import get_db


class Assignment:
    """Assignment of a problem to a university or industry partner."""

    STATUSES = ('pending', 'accepted', 'rejected', 'in_progress', 'completed')

    def __init__(self, id, problem_id, assignee_type, assignee_id,
                 status, created_by, created_at=None, updated_at=None,
                 notes=None):
        self.id = id
        self.problem_id = problem_id
        self.assignee_type = assignee_type  # 'university' or 'industry'
        self.assignee_id = assignee_id
        self.status = status  # pending, accepted, rejected, in_progress, completed
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at
        self.notes = notes

    def to_dict(self):
        return {
            'id': self.id,
            'problem_id': self.problem_id,
            'assignee_type': self.assignee_type,
            'assignee_id': self.assignee_id,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'notes': self.notes,
        }

    @staticmethod
    def create(problem_id, assignee_type, assignee_id, created_by, notes=None):
        if assignee_type not in ('university', 'industry'):
            raise ValueError("assignee_type must be 'university' or 'industry'")
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO assignments(problem_id, assignee_type, assignee_id,
                   created_by, status, notes)
                   VALUES(?,?,?,?,?,?)""",
                (problem_id, assignee_type, assignee_id, created_by, 'pending', notes)
            )
            aid = cur.lastrowid
            row = db.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone()
            return Assignment(**dict(row))

    @staticmethod
    def update_status(assignment_id, new_status):
        if new_status not in Assignment.STATUSES:
            raise ValueError(f"Status must be one of {Assignment.STATUSES}")
        with get_db() as db:
            db.execute(
                "UPDATE assignments SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (new_status, assignment_id)
            )

    @staticmethod
    def get_by_problem(problem_id):
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM assignments WHERE problem_id=?", (problem_id,)
            ).fetchall()
            return [Assignment(**dict(r)) for r in rows]

    @staticmethod
    def list_for_assignee(assignee_type, assignee_id):
        with get_db() as db:
            rows = db.execute(
                """SELECT * FROM assignments
                   WHERE assignee_type=? AND assignee_id=?
                   ORDER BY created_at DESC""",
                (assignee_type, assignee_id)
            ).fetchall()
            return [Assignment(**dict(r)) for r in rows]

    @staticmethod
    def list_all():
        with get_db() as db:
            rows = db.execute("SELECT * FROM assignments ORDER BY created_at DESC").fetchall()
            return [Assignment(**dict(r)) for r in rows]
