"""Notification model for in-app messaging."""
from database.db import get_db


class Notification:
    """In-app notification."""

    TYPES = ('assignment_created', 'status_changed', 'project_created',
             'milestone_completed', 'impact_recorded')

    def __init__(self, id, user_id, type, payload_json, read_at=None,
                 created_at=None):
        self.id = id
        self.user_id = user_id
        self.type = type
        self.payload_json = payload_json
        self.read_at = read_at
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'payload_json': self.payload_json,
            'read_at': self.read_at,
            'created_at': self.created_at,
        }

    @staticmethod
    def create(user_id, type, payload_json):
        if type not in Notification.TYPES:
            raise ValueError(f"Type must be one of {Notification.TYPES}")
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO notifications(user_id, type, payload_json)
                   VALUES(?,?,?)""",
                (user_id, type, payload_json)
            )
            nid = cur.lastrowid
            row = db.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
            return Notification(**dict(row))

    @staticmethod
    def list_for_user(user_id, unread_only=False):
        with get_db() as db:
            if unread_only:
                rows = db.execute(
                    """SELECT * FROM notifications
                       WHERE user_id=? AND read_at IS NULL
                       ORDER BY created_at DESC""",
                    (user_id,)
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT * FROM notifications
                       WHERE user_id=?
                       ORDER BY created_at DESC""",
                    (user_id,)
                ).fetchall()
            return [Notification(**dict(r)) for r in rows]

    @staticmethod
    def mark_read(notification_id, user_id):
        with get_db() as db:
            db.execute(
                """UPDATE notifications
                   SET read_at=CURRENT_TIMESTAMP
                   WHERE id=? AND user_id=?""",
                (notification_id, user_id)
            )
