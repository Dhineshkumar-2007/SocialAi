"""User model with role-based access."""
import hashlib
import secrets
from database.db import get_db


ROLES = ('citizen', 'admin', 'university', 'industry', 'faculty', 'student', 'government')


def hash_password(password: str) -> str:
    """Hash password with salt using PBKDF2."""
    salt = secrets.token_hex(16)
    hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_val.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against stored hash."""
    try:
        salt, hash_hex = stored.split('$')
        hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_val.hex() == hash_hex
    except Exception:
        return False


class User:
    """User model representing citizen, admin, university, or industry accounts."""

    def __init__(self, id, email, name, role, org_id=None, password_hash=None,
                 created_at=None, account_type='individual', position=None, department=None,
                 organization_name=None, phone=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.org_id = org_id
        self.password_hash = password_hash
        self.created_at = created_at
        self.account_type = account_type
        self.position = position
        self.department = department
        self.organization_name = organization_name
        self.phone = phone

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'org_id': self.org_id,
            'created_at': self.created_at,
            'account_type': self.account_type, 'position': self.position, 'department': self.department,
            'organization_name': self.organization_name, 'phone': self.phone,
        }

    @staticmethod
    def create(email, password, name, role, org_id=None, account_type='individual', position=None, department=None, organization_name=None, phone=None):
        """Create a new user."""
        if role not in ROLES:
            raise ValueError(f"Role must be one of {ROLES}")
        password_hash = hash_password(password)
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO users(email, password_hash, name, role, org_id, account_type, position, department, organization_name, phone)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (email, password_hash, name, role, org_id, account_type, position, department, organization_name, phone)
            )
            user_id = cur.lastrowid
            row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return User(**dict(row))

    @staticmethod
    def get_by_email(email):
        with get_db() as db:
            row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not row:
                return None
            return User(**dict(row))

    @staticmethod
    def get_by_id(user_id):
        with get_db() as db:
            row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                return None
            return User(**dict(row))

    @staticmethod
    def authenticate(email, password):
        """Authenticate user and return User if valid."""
        user = User.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

