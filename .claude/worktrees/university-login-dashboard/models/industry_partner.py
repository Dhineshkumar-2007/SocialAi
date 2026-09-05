"""Industry partner model for collaboration matching."""
from database.db import get_db


class IndustryPartner:
    """Industry partner with capabilities and sector."""

    def __init__(self, id, name, sector, region, capabilities_text,
                 embedding_json=None, contact_email=None,
                 created_at=None):
        self.id = id
        self.name = name
        self.sector = sector
        self.region = region
        self.capabilities_text = capabilities_text
        self.embedding_json = embedding_json
        self.contact_email = contact_email
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sector': self.sector,
            'region': self.region,
            'capabilities_text': self.capabilities_text,
            'embedding_json': self.embedding_json,
            'contact_email': self.contact_email,
            'created_at': self.created_at,
        }

    @staticmethod
    def create(name, sector, region, capabilities_text, contact_email=None):
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO industry_partners(name, sector, region,
                   capabilities_text, contact_email)
                   VALUES(?,?,?,?,?)""",
                (name, sector, region, capabilities_text, contact_email)
            )
            pid = cur.lastrowid
            row = db.execute("SELECT * FROM industry_partners WHERE id=?", (pid,)).fetchone()
            return IndustryPartner(**dict(row))

    @staticmethod
    def get_by_id(pid):
        with get_db() as db:
            row = db.execute("SELECT * FROM industry_partners WHERE id=?", (pid,)).fetchone()
            return IndustryPartner(**dict(row)) if row else None

    @staticmethod
    def list_all():
        with get_db() as db:
            rows = db.execute("SELECT * FROM industry_partners ORDER BY name").fetchall()
            return [IndustryPartner(**dict(r)) for r in rows]
