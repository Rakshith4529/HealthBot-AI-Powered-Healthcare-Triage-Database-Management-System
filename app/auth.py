import secrets
import time
from functools import wraps
from flask import session, redirect, url_for, request, jsonify, abort

# In-memory rate limiter: {ip: [timestamp, ...]}
_login_attempts: dict = {}
RATE_LIMIT_WINDOW = 900  # 15 minutes
RATE_LIMIT_MAX = 5


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    _login_attempts[ip] = attempts
    return len(attempts) >= RATE_LIMIT_MAX


def record_attempt(ip: str):
    _login_attempts.setdefault(ip, []).append(time.time())


def clear_attempts(ip: str):
    _login_attempts.pop(ip, None)


def generate_csrf_token() -> str:
    token = secrets.token_hex(32)
    session['csrf_token'] = token
    return token


def get_csrf_token() -> str:
    if 'csrf_token' not in session:
        return generate_csrf_token()
    return session['csrf_token']


def verify_csrf():
    token = (
        request.form.get('csrf_token')
        or request.headers.get('X-CSRF-Token')
        or (request.get_json(silent=True) or {}).get('csrf_token')
    )
    if not token or token != session.get('csrf_token'):
        if request.is_json:
            abort(jsonify({'error': 'CSRF validation failed'}), 403)
        abort(403)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'patient_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'patient_id' not in session:
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def doctor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'patient_id' not in session:
            return redirect(url_for('auth.login'))
        if session.get('role') != 'doctor':
            abort(403)
        return f(*args, **kwargs)
    return decorated
