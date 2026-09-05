from functools import wraps
from flask import session, jsonify, request


def require_role(*allowed_roles):
    """Decorator to restrict routes to specific roles."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session.get('user')
            if not user:
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': 'Authentication required'}), 401
                return jsonify({'error': 'Authentication required'}), 401
            if user.get('role') not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Return the current logged-in user from session."""
    return session.get('user')


def login_user(user_data):
    """Store user in session."""
    session['user'] = user_data
    session.permanent = True


def logout_user():
    """Clear user from session."""
    session.pop('user', None)
