"""
AI Tool Functions — each tool queries/mutates the DB and returns a structured dict.
"""
from datetime import datetime
import sqlite3


def list_appointments(patient_id: int, db) -> dict:
    cursor = db.cursor()
    cursor.execute("""
        SELECT a.Appointment_ID, a.Scheduled_At, a.Mode, a.Status, a.Notes,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name,
               s.Category_Name AS Specialization
        FROM APPOINTMENT a
        JOIN DOCTOR d ON a.Doctor_ID = d.Doctor_ID
        JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
        WHERE a.Patient_ID = ?
        ORDER BY a.Scheduled_At DESC
        LIMIT 10
    """, (patient_id,))
    rows = cursor.fetchall()
    return {"appointments": [dict(r) for r in rows]}


def book_appointment(patient_id: int, db, params: dict) -> dict:
    """Find the best-matching doctor and book the appointment."""
    doctor_name = params.get('doctor_name', '')
    date_str = params.get('date', '')
    time_str = params.get('time', '09:00')
    mode = params.get('mode', 'In-Person')
    specialization = params.get('specialization', '')

    cursor = db.cursor()

    # Find doctor by name or specialization
    doctor = None
    if doctor_name:
        parts = doctor_name.replace('Dr.', '').replace('Dr ', '').strip().split()
        for part in parts:
            cursor.execute("""
                SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
                       s.Category_Name AS Specialization
                FROM DOCTOR d
                JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
                WHERE d.First_Name LIKE ? OR d.Last_Name LIKE ?
                LIMIT 1
            """, (f'%{part}%', f'%{part}%'))
            doctor = cursor.fetchone()
            if doctor:
                break

    if not doctor and specialization:
        cursor.execute("""
            SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
                   s.Category_Name AS Specialization
            FROM DOCTOR d
            JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
            WHERE s.Category_Name LIKE ?
            LIMIT 1
        """, (f'%{specialization}%',))
        doctor = cursor.fetchone()

    if not doctor:
        # Pick first available doctor
        cursor.execute("""
            SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
                   s.Category_Name AS Specialization
            FROM DOCTOR d
            JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
            LIMIT 1
        """)
        doctor = cursor.fetchone()

    if not doctor:
        return {'success': False, 'error': 'No doctors found in the system.'}

    # Build scheduled datetime
    if not date_str:
        return {
            'success': False,
            'error': 'Please specify a date for the appointment.',
            'needs_date': True,
            'doctor': dict(doctor),
        }

    scheduled_at = f"{date_str} {time_str}:00"
    try:
        dt = datetime.strptime(scheduled_at, '%Y-%m-%d %H:%M:%S')
        if dt <= datetime.now():
            return {'success': False, 'error': 'Appointment date must be in the future.'}
    except ValueError:
        return {'success': False, 'error': f'Invalid date/time format: {scheduled_at}'}

    # Check conflicts
    cursor.execute("""
        SELECT 1 FROM APPOINTMENT
        WHERE Patient_ID = ? AND Scheduled_At = ? AND Status != 'Cancelled'
    """, (patient_id, scheduled_at))
    if cursor.fetchone():
        return {'success': False, 'error': 'You already have an appointment at this time.'}

    cursor.execute("""
        SELECT 1 FROM APPOINTMENT
        WHERE Doctor_ID = ? AND Scheduled_At = ? AND Status != 'Cancelled'
    """, (doctor['Doctor_ID'], scheduled_at))
    if cursor.fetchone():
        return {'success': False, 'error': 'Doctor is not available at that time. Please choose another slot.'}

    try:
        cursor.execute("""
            INSERT INTO APPOINTMENT (Patient_ID, Doctor_ID, Scheduled_At, Mode, Status)
            VALUES (?, ?, ?, ?, 'Scheduled')
        """, (patient_id, doctor['Doctor_ID'], scheduled_at, mode))
        appt_id = cursor.lastrowid
        db.commit()
        return {
            'success': True,
            'appointment_id': appt_id,
            'doctor': dict(doctor),
            'scheduled_at': scheduled_at,
            'mode': mode,
            'detail': f"with Dr. {doctor['Name']} on {dt.strftime('%B %d, %Y at %I:%M %p')} ({mode})",
        }
    except sqlite3.IntegrityError:
        db.rollback()
        return {'success': False, 'error': 'Booking conflict. Please choose a different time.'}


def cancel_appointment(patient_id: int, db, params: dict) -> dict:
    cursor = db.cursor()
    appt_id = params.get('appointment_id')

    if appt_id:
        cursor.execute(
            "SELECT Appointment_ID, Status FROM APPOINTMENT WHERE Appointment_ID = ? AND Patient_ID = ?",
            (appt_id, patient_id)
        )
    else:
        # Get most recent scheduled appointment
        cursor.execute("""
            SELECT Appointment_ID, Status FROM APPOINTMENT
            WHERE Patient_ID = ? AND Status = 'Scheduled'
            ORDER BY Scheduled_At ASC LIMIT 1
        """, (patient_id,))

    appt = cursor.fetchone()
    if not appt:
        return {'success': False, 'error': 'No matching appointment found to cancel.'}
    if appt['Status'] in ('Cancelled', 'Completed'):
        return {'success': False, 'error': f'Appointment is already {appt["Status"]}.'}

    cursor.execute(
        "UPDATE APPOINTMENT SET Status = 'Cancelled' WHERE Appointment_ID = ?",
        (appt['Appointment_ID'],)
    )
    db.commit()
    return {'success': True, 'appointment_id': appt['Appointment_ID']}


def get_medicines(patient_id: int, db) -> dict:
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.Prescription_ID, m.Name AS Medicine_Name, m.Category,
               p.Dosage_Instructions, p.Duration_Days, p.Prescribed_At,
               d.First_Name || ' ' || d.Last_Name AS Doctor_Name
        FROM PRESCRIPTION p
        JOIN MEDICINE m ON p.Medicine_ID = m.Medicine_ID
        LEFT JOIN DOCTOR d ON p.Doctor_ID = d.Doctor_ID
        WHERE p.Patient_ID = ?
        ORDER BY p.Prescribed_At DESC
    """, (patient_id,))
    rows = cursor.fetchall()
    return {"prescriptions": [dict(r) for r in rows]}


def find_doctors(db, params: dict) -> dict:
    cursor = db.cursor()
    specialization = params.get('specialization', '')
    if specialization:
        cursor.execute("""
            SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
                   d.Experience_Years, d.Bio, d.Rating, s.Category_Name AS Specialization
            FROM DOCTOR d
            JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
            WHERE s.Category_Name LIKE ?
            ORDER BY d.Rating DESC
        """, (f'%{specialization}%',))
    else:
        cursor.execute("""
            SELECT d.Doctor_ID, d.First_Name || ' ' || d.Last_Name AS Name,
                   d.Experience_Years, d.Bio, d.Rating, s.Category_Name AS Specialization
            FROM DOCTOR d
            JOIN SPECIALIZATION s ON d.Specialization_ID = s.Specialization_ID
            ORDER BY s.Category_Name, d.Rating DESC
        """)
    rows = cursor.fetchall()
    return {"doctors": [dict(r) for r in rows]}


def get_profile(patient_id: int, db) -> dict:
    cursor = db.cursor()
    cursor.execute(
        "SELECT Patient_ID, First_Name, Last_Name, DOB, Gender, Phone, Email, Created_At FROM PATIENT WHERE Patient_ID = ?",
        (patient_id,)
    )
    row = cursor.fetchone()
    return {"profile": dict(row) if row else {}}


def log_symptom(patient_id: int, db, params: dict, severity: str, escalated: bool) -> dict:
    symptoms = params.get('symptoms', [])
    symptoms_str = ', '.join(symptoms) if isinstance(symptoms, list) else str(symptoms)
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO SYMPTOM_LOG (Patient_ID, Symptoms, Severity, Is_Escalated)
        VALUES (?, ?, ?, ?)
    """, (patient_id, symptoms_str, severity, 1 if escalated else 0))
    db.commit()
    return {"logged": True, "symptoms": symptoms_str}
