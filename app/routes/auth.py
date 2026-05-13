import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db
from app.auth import (is_rate_limited, record_attempt, clear_attempts,
                      get_csrf_token, generate_csrf_token)

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'patient_id' in session:
        return _role_redirect()

    if request.method == 'POST':
        ip = request.remote_addr
        if is_rate_limited(ip):
            flash('Too many login attempts. Please wait 15 minutes.', 'danger')
            return render_template('auth/login.html', csrf_token=get_csrf_token()), 429

        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html', csrf_token=get_csrf_token())

        db  = get_db()
        row = db.execute(
            "SELECT Patient_ID, Password_Hash, Role, Is_Admin, Linked_Doctor_ID FROM PATIENT WHERE Email = ?",
            (email,)
        ).fetchone()

        if row and check_password_hash(row['Password_Hash'], password):
            clear_attempts(ip)
            session.clear()
            session['patient_id']       = row['Patient_ID']
            session['role']             = row['Role']            # 'patient' | 'doctor' | 'admin'
            session['is_admin']         = bool(row['Is_Admin'])
            session['linked_doctor_id'] = row['Linked_Doctor_ID']
            session['csrf_token']       = secrets.token_hex(32)
            session.permanent           = True

            db.execute(
                "INSERT INTO AUDIT_LOG (Patient_ID, Action, IP_Address) VALUES (?, 'login', ?)",
                (row['Patient_ID'], ip)
            )
            db.commit()

            next_url = request.args.get('next', '')
            if next_url.startswith('/'):
                return redirect(next_url)
            return _role_redirect()

        record_attempt(ip)
        flash('Invalid email or password.', 'danger')

    generate_csrf_token()
    return render_template('auth/login.html', csrf_token=get_csrf_token())


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if 'patient_id' in session:
        return _role_redirect()

    if request.method == 'POST':
        first    = request.form.get('first_name', '').strip()
        last     = request.form.get('last_name', '').strip()
        dob      = request.form.get('dob', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not all([first, last, dob, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html', csrf_token=get_csrf_token())
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/register.html', csrf_token=get_csrf_token())

        db = get_db()
        if db.execute("SELECT 1 FROM PATIENT WHERE Email = ?", (email,)).fetchone():
            flash('An account with that email already exists.', 'danger')
            return render_template('auth/register.html', csrf_token=get_csrf_token())

        hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        try:
            db.execute(
                "INSERT INTO PATIENT (First_Name, Last_Name, DOB, Email, Password_Hash, Role) VALUES (?,?,?,?,?,'patient')",
                (first, last, dob, email, hashed)
            )
            db.commit()
        except Exception:
            db.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('auth/register.html', csrf_token=get_csrf_token())

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    generate_csrf_token()
    return render_template('auth/register.html', csrf_token=get_csrf_token())


@auth.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if 'patient_id' in session:
        return _role_redirect()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        db = get_db()
        row = db.execute("SELECT Patient_ID FROM PATIENT WHERE Email = ?", (email,)).fetchone()
        
        if row:
            # In a real app, send an email. For demo, we store email in session and redirect to reset.
            session['reset_email'] = email
            flash('Password reset link has been verified! (Demo: Redirected to reset page)', 'success')
            return redirect(url_for('auth.reset_password'))
        else:
            # We don't want to leak whether the email exists or not usually, but for demo it's fine
            flash('If that email exists, a reset link will be sent.', 'info')
            return redirect(url_for('auth.login'))

    generate_csrf_token()
    return render_template('auth/forgot_password.html', csrf_token=get_csrf_token())


@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'patient_id' in session:
        return _role_redirect()

    reset_email = session.get('reset_email')
    if not reset_email:
        flash('Invalid or expired password reset session.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not password or password != confirm:
            flash('Passwords must match and cannot be empty.', 'danger')
            return render_template('auth/reset_password.html', csrf_token=get_csrf_token())
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/reset_password.html', csrf_token=get_csrf_token())

        db = get_db()
        hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        db.execute("UPDATE PATIENT SET Password_Hash = ? WHERE Email = ?", (hashed, reset_email))
        
        # Log the action
        row = db.execute("SELECT Patient_ID FROM PATIENT WHERE Email = ?", (reset_email,)).fetchone()
        if row:
            db.execute(
                "INSERT INTO AUDIT_LOG (Patient_ID, Action, IP_Address) VALUES (?, 'password_reset', ?)",
                (row['Patient_ID'], request.remote_addr)
            )
            
        db.commit()
        
        session.pop('reset_email', None)
        flash('Your password has been successfully reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    generate_csrf_token()
    return render_template('auth/reset_password.html', csrf_token=get_csrf_token())


def _role_redirect():
    """Send user to the right dashboard based on their role."""
    role = session.get('role', 'patient')
    if role == 'doctor':
        return redirect(url_for('doctor.dashboard'))
    if role == 'admin' or session.get('is_admin'):
        return redirect(url_for('admin.index'))
    return redirect(url_for('dashboard.index'))
