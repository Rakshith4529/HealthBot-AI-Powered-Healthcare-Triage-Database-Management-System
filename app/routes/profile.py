from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db
from app.auth import login_required, get_csrf_token, verify_csrf

profile = Blueprint('profile', __name__)


@profile.route('/profile', methods=['GET', 'POST'])
@login_required
def index():
    patient_id = session['patient_id']
    db = get_db()

    if request.method == 'POST':
        verify_csrf()
        first = request.form.get('first_name', '').strip()
        last = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', '').strip()
        dob = request.form.get('dob', '').strip()

        if not first or not last:
            flash('First and last name are required.', 'danger')
            return redirect(url_for('profile.index'))

        db.execute("""
            UPDATE PATIENT SET First_Name=?, Last_Name=?, Phone=?, Gender=?, DOB=?
            WHERE Patient_ID=?
        """, (first, last, phone, gender, dob, patient_id))
        db.execute(
            "INSERT INTO AUDIT_LOG (Patient_ID, Action, Details) VALUES (?, 'profile_update', 'Profile updated')",
            (patient_id,)
        )
        db.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.index'))

    patient = db.execute(
        "SELECT * FROM PATIENT WHERE Patient_ID = ?", (patient_id,)
    ).fetchone()

    if not patient:
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('profile.html', patient=patient, csrf_token=get_csrf_token())
