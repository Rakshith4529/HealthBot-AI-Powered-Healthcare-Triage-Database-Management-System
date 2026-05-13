from flask import Blueprint, render_template, request, session, jsonify, abort
from app.database import get_db
from app.auth import doctor_required, get_csrf_token, verify_csrf

doctor = Blueprint('doctor', __name__)


def _get_doctor_id():
    """Return the DOCTOR.Doctor_ID for the current logged-in doctor account."""
    return session.get('linked_doctor_id')


@doctor.route('/doctor/dashboard')
@doctor_required
def dashboard():
    doctor_id = _get_doctor_id()
    if not doctor_id:
        abort(403)

    db = get_db()

    # Doctor info
    doc = db.execute("""
        SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
               d.Experience_Years, d.Rating, d.Bio, s.Category_Name AS Specialization
        FROM DOCTOR d
        JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
        WHERE d.Doctor_ID = ?
    """, (doctor_id,)).fetchone()

    # Upcoming appointments for this doctor
    upcoming = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status, a.Notes,
               p.First_Name || ' ' || p.Last_Name AS Patient_Name,
               p.DOB, p.Gender, p.Phone, p.Email, p.Patient_ID
        FROM APPOINTMENT a
        JOIN PATIENT p ON a.Patient_ID = p.Patient_ID
        WHERE a.Doctor_ID = ? AND a.Status = 'Scheduled'
        ORDER BY a.Scheduled_At ASC
        LIMIT 10
    """, (doctor_id,)).fetchall()

    # All appointments (recent 20)
    all_appointments = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status, a.Notes,
               p.First_Name || ' ' || p.Last_Name AS Patient_Name, p.Patient_ID
        FROM APPOINTMENT a
        JOIN PATIENT p ON a.Patient_ID = p.Patient_ID
        WHERE a.Doctor_ID = ?
        ORDER BY a.Scheduled_At DESC
        LIMIT 20
    """, (doctor_id,)).fetchall()

    # Stats
    stats = {
        'total_patients': db.execute("""
            SELECT COUNT(DISTINCT Patient_ID) as c FROM APPOINTMENT WHERE Doctor_ID = ?
        """, (doctor_id,)).fetchone()['c'],
        'upcoming_count': db.execute("""
            SELECT COUNT(*) as c FROM APPOINTMENT WHERE Doctor_ID = ? AND Status = 'Scheduled'
        """, (doctor_id,)).fetchone()['c'],
        'completed_count': db.execute("""
            SELECT COUNT(*) as c FROM APPOINTMENT WHERE Doctor_ID = ? AND Status = 'Completed'
        """, (doctor_id,)).fetchone()['c'],
        'prescriptions_given': db.execute("""
            SELECT COUNT(*) as c FROM PRESCRIPTION WHERE Doctor_ID = ?
        """, (doctor_id,)).fetchone()['c'],
    }

    # My patients' recent AI chat symptoms (escalated ones first)
    patient_alerts = db.execute("""
        SELECT DISTINCT p.Patient_ID, p.First_Name || ' ' || p.Last_Name AS Patient_Name,
               sl.Symptoms, sl.Severity, sl.Is_Escalated, sl.Logged_At
        FROM SYMPTOM_LOG sl
        JOIN PATIENT p ON sl.Patient_ID = p.Patient_ID
        JOIN APPOINTMENT a ON a.Patient_ID = p.Patient_ID
        WHERE a.Doctor_ID = ?
        ORDER BY sl.Is_Escalated DESC, sl.Logged_At DESC
        LIMIT 5
    """, (doctor_id,)).fetchall()

    # My patients and their latest chat message (for doctor awareness)
    patient_chats = db.execute("""
        SELECT p.Patient_ID, p.First_Name || ' ' || p.Last_Name AS Patient_Name,
               cm.Content AS Last_Message, cm.Created_At, cm.Role, cm.Intent
        FROM CHAT_MESSAGE cm
        JOIN CHAT_SESSION cs ON cm.Session_ID = cs.Session_ID
        JOIN PATIENT p ON cs.Patient_ID = p.Patient_ID
        JOIN APPOINTMENT a ON a.Patient_ID = p.Patient_ID
        WHERE a.Doctor_ID = ? AND cm.Role = 'user'
        GROUP BY p.Patient_ID
        ORDER BY cm.Created_At DESC
        LIMIT 5
    """, (doctor_id,)).fetchall()

    # Doctor notes
    my_notes = db.execute("""
        SELECT dn.Note_ID, dn.Note, dn.Created_At,
               p.First_Name || ' ' || p.Last_Name AS Patient_Name
        FROM DOCTOR_NOTE dn
        JOIN PATIENT p ON dn.Patient_ID = p.Patient_ID
        WHERE dn.Doctor_ID = ?
        ORDER BY dn.Created_At DESC
        LIMIT 5
    """, (doctor_id,)).fetchall()

    return render_template('doctor/dashboard.html',
                           doc=doc,
                           upcoming=upcoming,
                           all_appointments=[dict(r) for r in all_appointments],
                           stats=stats,
                           patient_alerts=[dict(r) for r in patient_alerts],
                           patient_chats=[dict(r) for r in patient_chats],
                           my_notes=[dict(r) for r in my_notes],
                           csrf_token=get_csrf_token())


@doctor.route('/doctor/patient/<int:patient_id>')
@doctor_required
def patient_detail(patient_id):
    """View a specific patient's full record."""
    doctor_id = _get_doctor_id()
    db = get_db()

    # Verify this patient has an appointment with this doctor
    has_relation = db.execute("""
        SELECT 1 FROM APPOINTMENT WHERE Doctor_ID = ? AND Patient_ID = ? LIMIT 1
    """, (doctor_id, patient_id)).fetchone()
    if not has_relation:
        abort(403)

    patient = db.execute("SELECT * FROM PATIENT WHERE Patient_ID = ?", (patient_id,)).fetchone()
    appointments = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status, a.Notes,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name
        FROM APPOINTMENT a
        JOIN DOCTOR d ON a.Doctor_ID = d.Doctor_ID
        WHERE a.Patient_ID = ?
        ORDER BY a.Scheduled_At DESC
    """, (patient_id,)).fetchall()

    prescriptions = db.execute("""
        SELECT p.*, m.Name AS Medicine_Name, m.Category,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name
        FROM PRESCRIPTION p
        JOIN MEDICINE m ON p.Medicine_ID = m.Medicine_ID
        LEFT JOIN DOCTOR d ON p.Doctor_ID = d.Doctor_ID
        WHERE p.Patient_ID = ?
        ORDER BY p.Prescribed_At DESC
    """, (patient_id,)).fetchall()

    # Patient's AI chat history
    chat_msgs = db.execute("""
        SELECT cm.Role, cm.Content, cm.Intent, cm.Created_At
        FROM CHAT_MESSAGE cm
        JOIN CHAT_SESSION cs ON cm.Session_ID = cs.Session_ID
        WHERE cs.Patient_ID = ?
        ORDER BY cm.Created_At DESC
        LIMIT 20
    """, (patient_id,)).fetchall()

    # Symptom logs
    symptom_logs = db.execute("""
        SELECT Symptoms, Severity, Is_Escalated, Logged_At
        FROM SYMPTOM_LOG WHERE Patient_ID = ?
        ORDER BY Logged_At DESC LIMIT 10
    """, (patient_id,)).fetchall()

    # Doctor notes on this patient
    notes = db.execute("""
        SELECT dn.Note, dn.Created_At,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name
        FROM DOCTOR_NOTE dn
        JOIN DOCTOR d ON dn.Doctor_ID = d.Doctor_ID
        WHERE dn.Patient_ID = ?
        ORDER BY dn.Created_At DESC
    """, (patient_id,)).fetchall()

    return render_template('doctor/patient_detail.html',
                           patient=patient,
                           appointments=appointments,
                           prescriptions=prescriptions,
                           chat_msgs=chat_msgs,
                           symptom_logs=symptom_logs,
                           notes=notes,
                           doctor_id=doctor_id,
                           csrf_token=get_csrf_token())


@doctor.route('/doctor/appointments/update', methods=['POST'])
@doctor_required
def update_appointment():
    """Doctor marks appointment as Completed or Cancelled."""
    verify_csrf()
    doctor_id = _get_doctor_id()
    data      = request.get_json(silent=True) or {}
    appt_id   = data.get('appointment_id')
    status    = data.get('status')

    if status not in ('Completed', 'Cancelled', 'Scheduled'):
        return jsonify({'error': 'Invalid status'}), 400

    db = get_db()
    appt = db.execute(
        "SELECT 1 FROM APPOINTMENT WHERE Appointment_ID = ? AND Doctor_ID = ?",
        (appt_id, doctor_id)
    ).fetchone()
    if not appt:
        return jsonify({'error': 'Appointment not found or not yours'}), 404

    db.execute("UPDATE APPOINTMENT SET Status = ? WHERE Appointment_ID = ?", (status, appt_id))
    db.commit()
    return jsonify({'success': True, 'status': status})


@doctor.route('/doctor/note', methods=['POST'])
@doctor_required
def add_note():
    """Doctor adds a clinical note for a patient."""
    verify_csrf()
    doctor_id = _get_doctor_id()
    data      = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    note_text  = (data.get('note') or '').strip()

    if not note_text or not patient_id:
        return jsonify({'error': 'note and patient_id required'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO DOCTOR_NOTE (Doctor_ID, Patient_ID, Note) VALUES (?,?,?)",
        (doctor_id, patient_id, note_text)
    )
    db.commit()
    return jsonify({'success': True})


@doctor.route('/doctor/appointments/api')
@doctor_required
def appointments_api():
    """Live JSON feed of doctor's appointments (for real-time sync demo)."""
    doctor_id = _get_doctor_id()
    db = get_db()
    rows = db.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status,
               p.First_Name || ' ' || p.Last_Name AS Patient_Name
        FROM APPOINTMENT a
        JOIN PATIENT p ON a.Patient_ID = p.Patient_ID
        WHERE a.Doctor_ID = ?
        ORDER BY a.Scheduled_At ASC
    """, (doctor_id,)).fetchall()
    return jsonify([dict(r) for r in rows])
