"""Authentication routes."""
import os
from flask import Blueprint, request, jsonify, session
from auth.decorators import login_user, logout_user, require_role
from auth.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
__all__ = ['auth_bp']


@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', 'citizen')
    org_id = data.get('org_id')

    if not email or not password or not name:
        return jsonify({'error': 'email, password, and name required'}), 400

    # Only admins can create admin accounts; faculty/student need a university org_id
    if role == 'admin':
        return jsonify({'error': 'admin accounts cannot be self-registered'}), 403

    try:
        user = User.create(email, password, name, role, org_id=org_id)
        return jsonify({
            'message': 'User registered',
            'user': user.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as exc:
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400

    user = User.authenticate(email, password)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    user_dict = user.to_dict()
    # Remove sensitive fields
    user_dict.pop('password_hash', None)
    login_user(user_dict)
    return jsonify({
        'message': 'Login successful',
        'user': user_dict
    }), 200


@auth_bp.post('/register/university')
def register_university():
    """Dedicated university registration — does not touch public /register."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    org_id = data.get('org_id')

    if not email or not password or not name:
        return jsonify({'error': 'email, password, and name required'}), 400
    if not org_id:
        return jsonify({'error': 'org_id required — select your institution'}), 400
    try:
        org_id = int(org_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'org_id must be a valid institution id'}), 400

    # Enforce university-only role; never allow citizen/admin/industry here.
    role = 'university'

    # Reject public email providers — institutional email required
    domain = email.split('@')[-1].lower() if '@' in email else ''
    blocked = {'gmail.com','yahoo.com','yahoo.co.in','outlook.com','hotmail.com',
               'live.com','icloud.com','me.com','aol.com','protonmail.com','zoho.com',
               'yandex.com','rediffmail.com','mail.com','gmx.com','msn.com'}
    if domain in blocked:
        return jsonify({'error': 'Please use an official university email address'}), 400

    # Verify the selected org_id actually exists in the universities table
    from database.db import get_db
    with get_db() as db:
        row = db.execute("SELECT id FROM universities WHERE id=?", (org_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Selected institution not found'}), 400

    # Check duplicate email
    if User.get_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409

    # Password min length
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    try:
        user = User.create(email, password, name, role, org_id=org_id)
        user_dict = user.to_dict()
        user_dict.pop('password_hash', None)
        return jsonify({'message': 'University account registered', 'user': user_dict}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as exc:
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.post('/logout')
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200


@auth_bp.get('/me')
@require_role('citizen', 'admin', 'university', 'industry')
def me():
    user = session.get('user')
    return jsonify({'user': user}), 200
