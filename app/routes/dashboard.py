from flask import Blueprint, render_template, session
from app.database import get_db
from app.auth import login_required

dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/')
@dashboard.route('/dashboard')
@login_required
def index():
    patient_id = session['patient_id']
    db = get_db()

    # Patient info
    patient = db.execute(
        "SELECT First_Name, Last_Name FROM PATIENT WHERE Patient_ID = ?", (patient_id,)
    ).fetchone()

    # Upcoming appointments
    appointments = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name,
               s.Category_Name AS Specialization
        FROM APPOINTMENT a
        JOIN DOCTOR d ON a.Doctor_ID = d.Doctor_ID
        JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
        WHERE a.Patient_ID = ? AND a.Status = 'Scheduled'
        ORDER BY a.Scheduled_At ASC
        LIMIT 5
    """, (patient_id,)).fetchall()

    # Active prescriptions count
    rx_count = db.execute(
        "SELECT COUNT(*) as cnt FROM PRESCRIPTION WHERE Patient_ID = ?", (patient_id,)
    ).fetchone()['cnt']

    # Chat sessions count
    chat_count = db.execute(
        "SELECT COUNT(*) as cnt FROM CHAT_SESSION WHERE Patient_ID = ?", (patient_id,)
    ).fetchone()['cnt']

    # Total appointments count
    appt_count = db.execute(
        "SELECT COUNT(*) as cnt FROM APPOINTMENT WHERE Patient_ID = ?", (patient_id,)
    ).fetchone()['cnt']

    # Recent chat messages
    recent_chats = db.execute("""
        SELECT cm.Content, cm.Role, cm.Created_At
        FROM CHAT_MESSAGE cm
        JOIN CHAT_SESSION cs ON cm.Session_ID = cs.Session_ID
        WHERE cs.Patient_ID = ? AND cm.Role = 'assistant'
        ORDER BY cm.Created_At DESC
        LIMIT 3
    """, (patient_id,)).fetchall()

    return render_template('dashboard.html',
                           patient=patient,
                           appointments=appointments,
                           rx_count=rx_count,
                           chat_count=chat_count,
                           appt_count=appt_count,
                           recent_chats=recent_chats)
