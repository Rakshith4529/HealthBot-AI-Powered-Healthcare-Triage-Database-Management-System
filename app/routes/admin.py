from flask import Blueprint, render_template, session, jsonify
from app.database import get_db
from app.auth import admin_required

admin = Blueprint('admin', __name__)


@admin.route('/admin')
@admin_required
def index():
    db = get_db()
    stats = {
        'patients': db.execute("SELECT COUNT(*) as c FROM PATIENT WHERE Is_Admin=0").fetchone()['c'],
        'doctors':  db.execute("SELECT COUNT(*) as c FROM DOCTOR").fetchone()['c'],
        'appointments': db.execute("SELECT COUNT(*) as c FROM APPOINTMENT").fetchone()['c'],
        'chats': db.execute("SELECT COUNT(*) as c FROM CHAT_SESSION").fetchone()['c'],
    }
    patients = db.execute("""
        SELECT Patient_ID, First_Name || ' ' || Last_Name AS Name, Email,
               Created_At, Is_Admin
        FROM PATIENT ORDER BY Created_At DESC LIMIT 50
    """).fetchall()
    doctors = db.execute("""
        SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
               d.Experience_Years, d.Rating, s.Category_Name AS Specialization
        FROM DOCTOR d
        JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
        ORDER BY s.Category_Name
    """).fetchall()
    appointments = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status,
               p.First_Name || ' ' || p.Last_Name AS Patient_Name,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name
        FROM APPOINTMENT a
        JOIN PATIENT p ON a.Patient_ID = p.Patient_ID
        JOIN DOCTOR d ON a.Doctor_ID = d.Doctor_ID
        ORDER BY a.Scheduled_At DESC LIMIT 50
    """).fetchall()
    return render_template('admin.html',
                           stats=stats,
                           patients=[dict(r) for r in patients],
                           doctors=[dict(r) for r in doctors],
                           appointments=[dict(r) for r in appointments])


@admin.route('/admin/api/stats')
@admin_required
def api_stats():
    db = get_db()
    return jsonify({
        'patients': db.execute("SELECT COUNT(*) as c FROM PATIENT WHERE Is_Admin=0").fetchone()['c'],
        'doctors': db.execute("SELECT COUNT(*) as c FROM DOCTOR").fetchone()['c'],
        'appointments': db.execute("SELECT COUNT(*) as c FROM APPOINTMENT").fetchone()['c'],
    })
