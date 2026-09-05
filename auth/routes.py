"""Authentication routes."""
import os
from flask import Blueprint, request, jsonify, session, current_app
from auth.decorators import login_user, logout_user, require_role
from auth.models import User
from database.db import get_db

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
@require_role('citizen', 'admin', 'university', 'industry', 'faculty', 'student')
def me():
    user = session.get('user')
    return jsonify({'user': user}), 200


@auth_bp.post('/register/common')
def register_common():
    """Unified registration for Person, Institution, and Government accounts.

    Account types:
      person       – citizen who reports and tracks problems
      institution  – university / college / NGO / industry with capability profile
      government   – official public authority with department and jurisdiction
    """
    data = request.get_json() or {}

    # --- normalise account_type ------------------------------------------------
    account_type = (data.get('account_type') or 'person').strip().lower()
    # Accept legacy 'individual' from older front-ends / deep-links
    if account_type == 'individual':
        account_type = 'person'

    if account_type not in ('person', 'institution', 'government'):
        return jsonify({'error': 'Invalid account type'}), 400

    # --- common fields --------------------------------------------------------
    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    phone    = (data.get('phone') or '').strip()
    location = (data.get('location') or '').strip()

    position      = (data.get('position') or '').strip()
    department    = (data.get('department') or '').strip()
    organization_name = (data.get('organization_name') or '').strip()
    jurisdiction  = (data.get('jurisdiction') or '').strip()

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    institution_org_id = None

    # Password is required for all account types including institution
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if User.get_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409

    # --- INSTITUTION ----------------------------------------------------------
    if account_type == 'institution':
        org = data.get('institution') or {}
        org_name = (org.get('name') or '').strip()
        if not org_name or not org.get('institution_type'):
            return jsonify({'error': 'Institution name and institution type are required'}), 400
        try:
            with get_db() as db:
                cur = db.execute(
                    '''INSERT INTO universities(
                           name,city,description,capacity,institution_type,
                           website,address,state,pincode,contact_phone,
                           contact_email,email_domain,accreditation,
                           research_summary,expertise_summary,
                           programs_summary,facilities_summary,
                           verified)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (org_name, org.get('city'), org.get('description', ''),
                     int(org.get('capacity') or 10), org.get('institution_type'),
                     org.get('website'), org.get('address'),
                     org.get('state', 'Tamil Nadu'), org.get('pincode'),
                     org.get('contact_phone'), email, email.split('@')[-1],
                     org.get('accreditation'), org.get('research_summary', ''),
                     org.get('expertise_summary', ''),
                     org.get('programs_summary', ''),
                     org.get('facilities_summary', ''),
                     0))
                org_id = cur.lastrowid
                for x in org.get('research_areas', []):
                    if x.get('area'):
                        db.execute(
                            'INSERT INTO institution_research_areas(university_id,area,keywords) VALUES(?,?,?)',
                            (org_id, x['area'], x.get('keywords', '')))
                for x in org.get('facilities', []):
                    if x.get('name'):
                        db.execute(
                            'INSERT INTO institution_facilities(university_id,name,type,capabilities) VALUES(?,?,?,?)',
                            (org_id, x['name'], x.get('type'), x.get('capabilities', '')))
                for x in org.get('programs', []):
                    if x.get('name'):
                        db.execute(
                            'INSERT INTO institution_programs(university_id,name,department,focus) VALUES(?,?,?,?)',
                            (org_id, x['name'], x.get('department'), x.get('focus', '')))
                for x in org.get('faculty', []):
                    if x.get('name'):
                        db.execute(
                            'INSERT INTO faculty(university_id,name,department,expertise) VALUES(?,?,?,?)',
                            (org_id, x['name'], x.get('department'), x.get('expertise', '')))
                for x in org.get('previous_projects', []):
                    if x.get('title'):
                        db.execute(
                            'INSERT INTO previous_projects(university_id,title,description) VALUES(?,?,?)',
                            (org_id, x['title'], x.get('description', '')))
        except Exception as exc:
            current_app.logger.exception("Institution registration failed")
            return jsonify({'error': 'Institution registration failed'}), 400
        role = 'university'
        organization_name = org_name
        institution_org_id = org_id

    # --- GOVERNMENT -----------------------------------------------------------
    elif account_type == 'government':
        if not position:
            return jsonify({'error': 'Official position is required for government accounts'}), 400
        if not department:
            return jsonify({'error': 'Department / agency is required for government accounts'}), 400
        if not organization_name:
            return jsonify({'error': 'Government organization is required'}), 400
        role = 'citizen'
        # Store jurisdiction in organization_name for government accounts
        organization_name = f"{organization_name} | {department}"
        if jurisdiction:
            organization_name += f" | {jurisdiction}"

    # --- PERSON ---------------------------------------------------------------
    else:
        role = 'citizen'
        position = None
        department = None
        # Use location as the organization_name for person accounts
        organization_name = location or None

    # --- create user ----------------------------------------------------------
    try:
        user = User.create(
            email, password, name, role,
            org_id=institution_org_id if account_type == 'institution' else None,
            account_type=account_type,
            position=position or None,
            department=department or None,
            organization_name=organization_name,
            phone=phone or None,
        )
        return jsonify({'message': 'Registration successful', 'user': user.to_dict()}), 201
    except Exception as exc:
        current_app.logger.exception("Registration failed")
        return jsonify({'error': 'Registration failed'}), 400
