"""
seed.py — Wipes and re-seeds the MedAssist database.
Run: python seed.py
Demo Accounts:
  Patients : alice@demo.com / bob@demo.com / carol@demo.com  (Demo1234!)
  Doctors  : dr.carter@medassist.com / dr.thompson@medassist.com / dr.brown@medassist.com (Doctor1234!)
  Admin    : admin@medassist.com  (Admin1234!)
"""
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join('instance', 'medassist.db')
SCHEMA  = 'schema.sql'


def h(pw):
    return generate_password_hash(pw, method='pbkdf2:sha256', salt_length=16)


def seed():
    os.makedirs('instance', exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("[OK] Old database removed")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    with open(SCHEMA, 'r') as f:
        conn.executescript(f.read())
    print("[OK] Schema applied")

    # ── Specializations ───────────────────────────────────────────────────────
    specs = ['General Practice', 'Cardiology', 'Pediatrics',
             'Dermatology', 'Orthopedics', 'Neurology']
    for s in specs:
        conn.execute("INSERT INTO SPECIALIZATION (Category_Name) VALUES (?)", (s,))
    conn.commit()
    print(f"[OK] {len(specs)} specializations")

    # ── Doctors ───────────────────────────────────────────────────────────────
    doctors = [
        # (First, Last, Exp, Spec_ID, Bio, Rating)
        ('Emily',    'Carter',   12, 1, 'Experienced GP focused on preventive care and chronic disease management.', 4.8),
        ('James',    'Wilson',   20, 1, 'Senior general practitioner with two decades of family medicine experience.', 4.7),
        ('Sarah',    'Thompson', 15, 2, 'Cardiologist specialising in heart failure, arrhythmia, and preventive cardiology.', 4.9),
        ('Michael',  'Davis',    10, 2, 'Interventional cardiologist skilled in angioplasty and stent procedures.', 4.6),
        ('Linda',    'Brown',     8, 3, 'Paediatrician focused on child health, vaccination, and developmental care.', 4.9),
        ('Robert',   'Miller',   18, 4, 'Dermatologist treating acne, eczema, psoriasis, and skin cancer screening.', 4.7),
        ('Jennifer', 'Garcia',    5, 5, 'Orthopaedic surgeon specialising in sports injuries and joint replacements.', 4.5),
        ('David',    'Martinez', 14, 6, 'Neurologist experienced in migraines, epilepsy, and MS management.', 4.8),
    ]
    for d in doctors:
        conn.execute("""
            INSERT INTO DOCTOR (First_Name, Last_Name, Experience_Years,
                                Specialization_ID, Bio, Rating)
            VALUES (?,?,?,?,?,?)
        """, d)
    conn.commit()
    print(f"[OK] {len(doctors)} doctors")

    # Doctor IDs: Emily=1, James=2, Sarah=3, Michael=4, Linda=5, Robert=6, Jennifer=7, David=8

    # ── Patient Accounts ──────────────────────────────────────────────────────
    # (First, Last, DOB, Gender, Phone, Email, Password, Role, Is_Admin, Linked_Doctor_ID)
    patients = [
        # Patients
        ('Alice',  'Johnson',  '1990-04-15', 'Female', '555-0101', 'alice@demo.com',          'Demo1234!',   'patient', 0, None),
        ('Bob',    'Martinez', '1985-07-22', 'Male',   '555-0102', 'bob@demo.com',            'Demo1234!',   'patient', 0, None),
        ('Carol',  'Williams', '1995-11-03', 'Female', '555-0103', 'carol@demo.com',          'Demo1234!',   'patient', 0, None),
        ('David',  'Lee',      '1978-02-14', 'Male',   '555-0104', 'david@demo.com',          'Demo1234!',   'patient', 0, None),
        ('Emma',   'Davis',    '2001-09-30', 'Female', '555-0105', 'emma@demo.com',           'Demo1234!',   'patient', 0, None),

        # Doctor Accounts (linked to DOCTOR records)
        ('Emily',   'Carter',   '1982-06-10', 'Female', '555-1001', 'dr.carter@medassist.com',   'Doctor1234!', 'doctor',  0, 1),
        ('Sarah',   'Thompson', '1979-03-22', 'Female', '555-1003', 'dr.thompson@medassist.com', 'Doctor1234!', 'doctor',  0, 3),
        ('Linda',   'Brown',    '1988-11-05', 'Female', '555-1005', 'dr.brown@medassist.com',    'Doctor1234!', 'doctor',  0, 5),

        # Admin
        ('Admin',  'MedAssist', '1980-01-01', 'Other', '555-0000', 'admin@medassist.com',     'Admin1234!',  'admin',   1, None),
    ]
    for p in patients:
        conn.execute("""
            INSERT INTO PATIENT
                (First_Name, Last_Name, DOB, Gender, Phone, Email,
                 Password_Hash, Role, Is_Admin, Linked_Doctor_ID)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (*p[:6], h(p[6]), *p[7:]))
    conn.commit()
    print(f"[OK] {len(patients)} user accounts  ({len([p for p in patients if p[7]=='patient'])} patients, "
          f"{len([p for p in patients if p[7]=='doctor'])} doctors, 1 admin)")

    # ── Medicines ─────────────────────────────────────────────────────────────
    medicines = [
        ('Paracetamol',   'Analgesic',      'Pain reliever and fever reducer.',                   '500 mg every 6 hours'),
        ('Ibuprofen',     'NSAID',           'Anti-inflammatory pain reliever.',                   '400 mg every 8 hours with food'),
        ('Amoxicillin',   'Antibiotic',      'Broad-spectrum antibiotic for bacterial infections.','500 mg every 8 hours for 7 days'),
        ('Cetirizine',    'Antihistamine',   'Allergy relief medication.',                         '10 mg once daily'),
        ('Omeprazole',    'PPI',             'Treats acid reflux and stomach ulcers.',             '20 mg before meals'),
        ('Metformin',     'Antidiabetic',    'Controls blood sugar in type 2 diabetes.',           '500 mg twice daily with meals'),
        ('Lisinopril',    'ACE Inhibitor',   'Treats high blood pressure.',                        '10 mg once daily'),
        ('Atorvastatin',  'Statin',          'Lowers cholesterol levels.',                         '20 mg once at bedtime'),
        ('Salbutamol',    'Bronchodilator',  'Relieves bronchospasm in asthma.',                   '2 puffs as needed'),
        ('Loratadine',    'Antihistamine',   'Non-drowsy allergy medication.',                     '10 mg once daily'),
        ('Metoprolol',    'Beta-Blocker',    'Controls heart rate and blood pressure.',            '25 mg twice daily'),
        ('Warfarin',      'Anticoagulant',   'Prevents blood clots.',                              '5 mg once daily (dose varies)'),
    ]
    for m in medicines:
        conn.execute("INSERT INTO MEDICINE (Name, Category, Description, Common_Dosage) VALUES (?,?,?,?)", m)
    conn.commit()
    print(f"[OK] {len(medicines)} medicines")

    # ── Prescriptions ─────────────────────────────────────────────────────────
    # (Patient_ID, Doctor_ID, Medicine_ID, Instructions, Duration_Days)
    prescriptions = [
        (1, 1, 1,  'Take 500 mg every 6 hours for pain relief.',        10),
        (1, 1, 4,  'Take 10 mg once daily for seasonal allergies.',      30),
        (2, 3, 7,  'Take 10 mg once daily to manage blood pressure.',    90),
        (2, 3, 8,  'Take 20 mg at bedtime to lower cholesterol.',        90),
        (2, 3, 11, 'Take 25 mg twice daily for heart rate control.',     60),
        (3, 1, 5,  'Take 20 mg before breakfast for acid reflux.',       30),
        (3, 1, 10, 'Take 10 mg once daily for allergies.',               30),
        (4, 3, 12, 'Take 5 mg daily — INR monitoring required weekly.',  180),
        (4, 3, 11, 'Take 25 mg twice daily.',                            90),
        (5, 5, 1,  'Take 250 mg every 8 hours as needed.',               5),
        (5, 5, 3,  'Take 250 mg three times daily for infection.',       7),
    ]
    for rx in prescriptions:
        conn.execute("""
            INSERT INTO PRESCRIPTION
                (Patient_ID, Doctor_ID, Medicine_ID, Dosage_Instructions, Duration_Days)
            VALUES (?,?,?,?,?)
        """, rx)
    conn.commit()
    print(f"[OK] {len(prescriptions)} prescriptions")

    # ── Appointments ──────────────────────────────────────────────────────────
    # (Patient_ID, Doctor_ID, Scheduled_At, Mode, Status, Notes)
    appointments = [
        # Alice (P1) with Dr. Carter (D1)
        (1, 1, '2026-05-15 10:00:00', 'In-Person',    'Scheduled',  'Follow-up for allergy management'),
        (1, 3, '2026-05-20 14:30:00', 'Telemedicine', 'Scheduled',  'Cardiology review — ECG results'),
        (1, 1, '2026-04-10 09:00:00', 'In-Person',    'Completed',  'Annual health check'),

        # Bob (P2) with Dr. Thompson (D3)
        (2, 3, '2026-05-25 11:00:00', 'In-Person',    'Scheduled',  'Blood pressure medication review'),
        (2, 3, '2026-05-12 09:00:00', 'Telemedicine', 'Completed',  'Cholesterol results discussion'),
        (2, 4, '2026-06-02 15:00:00', 'In-Person',    'Scheduled',  'Interventional cardiology consult'),

        # Carol (P3) with Dr. Carter (D1) and Dr. Brown (D5)
        (3, 1, '2026-05-18 15:00:00', 'Telemedicine', 'Scheduled',  'Acid reflux follow-up'),
        (3, 5, '2026-05-30 10:30:00', 'In-Person',    'Scheduled',  'Paediatrics wellness check'),
        (3, 1, '2026-04-20 11:00:00', 'In-Person',    'Completed',  'Initial consultation'),

        # David (P4) with Dr. Thompson (D3)
        (4, 3, '2026-05-22 09:00:00', 'In-Person',    'Scheduled',  'Anticoagulation management'),
        (4, 3, '2026-05-08 14:00:00', 'In-Person',    'Completed',  'INR check and warfarin dosing'),

        # Emma (P5) with Dr. Brown (D5)
        (5, 5, '2026-05-16 13:00:00', 'In-Person',    'Scheduled',  'Paediatric health review'),
        (5, 1, '2026-05-28 10:00:00', 'Telemedicine', 'Scheduled',  'GP consult for recurring cough'),
    ]
    for a in appointments:
        conn.execute("""
            INSERT INTO APPOINTMENT
                (Patient_ID, Doctor_ID, Scheduled_At, Mode, Status, Notes)
            VALUES (?,?,?,?,?,?)
        """, a)
    conn.commit()
    print(f"[OK] {len(appointments)} appointments")

    # ── Doctor Notes ──────────────────────────────────────────────────────────
    notes = [
        (1, 1, 3,  'Annual check completed. BP 118/76. Recommended continued allergy medication. Next review in 6 months.'),
        (3, 2, 5,  'Cholesterol levels improving. LDL down 18% since last visit. Continue current statin. Monitor monthly.'),
        (3, 2, 11, 'Warfarin INR = 2.4 (target 2.0–3.0). Dosing appropriate. Re-check in 7 days.'),
        (1, 3, 9,  'Acid reflux well-controlled on omeprazole. Advised dietary modifications. Continue for 30 days.'),
    ]
    for n in notes:
        conn.execute("""
            INSERT INTO DOCTOR_NOTE (Doctor_ID, Patient_ID, Appointment_ID, Note)
            VALUES (?,?,?,?)
        """, n)
    conn.commit()
    print(f"[OK] {len(notes)} doctor notes")

    # ── Chat Sessions + Messages ──────────────────────────────────────────────
    # Session for Alice
    conn.execute("INSERT INTO CHAT_SESSION (Patient_ID) VALUES (1)")
    # Session for Bob
    conn.execute("INSERT INTO CHAT_SESSION (Patient_ID) VALUES (2)")
    # Session for Carol
    conn.execute("INSERT INTO CHAT_SESSION (Patient_ID) VALUES (3)")
    conn.commit()

    s1 = conn.execute("SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID=1").fetchone()['Session_ID']
    s2 = conn.execute("SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID=2").fetchone()['Session_ID']
    s3 = conn.execute("SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID=3").fetchone()['Session_ID']

    chat_msgs = [
        # Alice's session
        (s1,'user',      'I have a headache and slight fever.',         'symptom_check'),
        (s1,'assistant', 'I\'ve noted your symptoms. For headache, rest in a quiet room and take ibuprofen if needed. For fever, take paracetamol 500 mg. Since you have multiple symptoms, see a doctor if they persist beyond 48 hours.', 'symptom_check'),
        (s1,'user',      'Can I book an appointment with Dr. Carter?',  'book_appointment'),
        (s1,'assistant', 'Appointment booked with Dr. Emily Carter on May 15, 2026 at 10:00 AM (In-Person)!', 'book_appointment'),
        (s1,'user',      'What medicines am I taking?',                 'get_medicines'),
        (s1,'assistant', 'You are currently prescribed: Paracetamol 500 mg every 6 hours and Cetirizine 10 mg daily, both prescribed by Dr. Emily Carter.', 'get_medicines'),

        # Bob's session
        (s2,'user',      'Show me my upcoming appointments.',           'list_appointments'),
        (s2,'assistant', 'You have 2 upcoming appointments: Dr. Sarah Thompson on May 25 (In-Person) and Dr. Michael Davis on Jun 2 (In-Person).', 'list_appointments'),
        (s2,'user',      'I have chest tightness and shortness of breath.', 'symptom_check'),
        (s2,'assistant', '🚨 CRITICAL: These symptoms could indicate a serious cardiac event. Please call emergency services immediately or go to the nearest emergency room. Do not delay.', 'symptom_check'),

        # Carol's session
        (s3,'user',      'Find me a cardiologist.',                     'find_doctors'),
        (s3,'assistant', 'Here are available cardiologists: Dr. Sarah Thompson (15 yrs, Rating 4.9) and Dr. Michael Davis (10 yrs, Rating 4.6).', 'find_doctors'),
        (s3,'user',      'Show my prescriptions.',                      'get_medicines'),
        (s3,'assistant', 'You are prescribed: Omeprazole 20 mg before breakfast and Loratadine 10 mg daily, both by Dr. Emily Carter.', 'get_medicines'),
    ]
    for m in chat_msgs:
        conn.execute("INSERT INTO CHAT_MESSAGE (Session_ID, Role, Content, Intent) VALUES (?,?,?,?)", m)
    conn.commit()
    print(f"[OK] {len(chat_msgs)} chat messages across 3 sessions")

    conn.close()

    print("\n" + "="*60)
    print("  MedAssist 2.0 — Database Seeded!")
    print("="*60)
    print("""
  PATIENT ACCOUNTS           EMAIL                        PASSWORD
  ─────────────────────────────────────────────────────────────────
  Alice Johnson (patient)    alice@demo.com               Demo1234!
  Bob Martinez  (patient)    bob@demo.com                 Demo1234!
  Carol Williams(patient)    carol@demo.com               Demo1234!
  David Lee     (patient)    david@demo.com               Demo1234!
  Emma Davis    (patient)    emma@demo.com                Demo1234!

  DOCTOR ACCOUNTS            EMAIL                        PASSWORD
  ─────────────────────────────────────────────────────────────────
  Dr. Emily Carter (GP)      dr.carter@medassist.com      Doctor1234!
  Dr. Sarah Thompson (Cardio)dr.thompson@medassist.com    Doctor1234!
  Dr. Linda Brown (Paeds)    dr.brown@medassist.com       Doctor1234!

  ADMIN                      EMAIL                        PASSWORD
  ─────────────────────────────────────────────────────────────────
  Admin                      admin@medassist.com          Admin1234!

  Run:  python run.py
  Open: http://localhost:5000
""")


if __name__ == '__main__':
    seed()
