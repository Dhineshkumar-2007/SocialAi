from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

from auth import routes  # noqa: F401

__all__ = ['auth_bp']