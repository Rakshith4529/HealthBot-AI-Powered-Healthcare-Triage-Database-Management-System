-- MedAssist 2.0 — Database Schema (with Doctor Accounts)
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS PATIENT (
    Patient_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
    First_Name       TEXT NOT NULL,
    Last_Name        TEXT NOT NULL,
    DOB              TEXT,
    Gender           TEXT,
    Phone            TEXT,
    Email            TEXT NOT NULL UNIQUE,
    Password_Hash    TEXT NOT NULL,
    Role             TEXT NOT NULL DEFAULT 'patient',   -- 'patient' | 'doctor' | 'admin'
    Is_Admin         INTEGER DEFAULT 0,
    Linked_Doctor_ID INTEGER,                           -- FK to DOCTOR (for doctor accounts)
    Created_At       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Linked_Doctor_ID) REFERENCES DOCTOR(Doctor_ID) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS SPECIALIZATION (
    Specialization_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Category_Name     TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS DOCTOR (
    Doctor_ID         INTEGER PRIMARY KEY AUTOINCREMENT,
    First_Name        TEXT NOT NULL,
    Last_Name         TEXT NOT NULL,
    Experience_Years  INTEGER DEFAULT 0,
    Specialization_ID INTEGER NOT NULL,
    Bio               TEXT,
    Rating            REAL DEFAULT 4.5,
    FOREIGN KEY (Specialization_ID) REFERENCES SPECIALIZATION(Specialization_ID)
);

CREATE TABLE IF NOT EXISTS MEDICINE (
    Medicine_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
    Name          TEXT NOT NULL,
    Category      TEXT,
    Description   TEXT,
    Common_Dosage TEXT
);

CREATE TABLE IF NOT EXISTS PRESCRIPTION (
    Prescription_ID     INTEGER PRIMARY KEY AUTOINCREMENT,
    Patient_ID          INTEGER NOT NULL,
    Doctor_ID           INTEGER,
    Medicine_ID         INTEGER NOT NULL,
    Dosage_Instructions TEXT,
    Prescribed_At       DATETIME DEFAULT CURRENT_TIMESTAMP,
    Duration_Days       INTEGER,
    FOREIGN KEY (Patient_ID)  REFERENCES PATIENT(Patient_ID)   ON DELETE CASCADE,
    FOREIGN KEY (Doctor_ID)   REFERENCES DOCTOR(Doctor_ID)     ON DELETE SET NULL,
    FOREIGN KEY (Medicine_ID) REFERENCES MEDICINE(Medicine_ID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS APPOINTMENT (
    Appointment_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Patient_ID     INTEGER NOT NULL,
    Doctor_ID      INTEGER NOT NULL,
    Scheduled_At   DATETIME NOT NULL,
    Mode           TEXT DEFAULT 'In-Person',
    Status         TEXT DEFAULT 'Scheduled',
    Notes          TEXT,
    FOREIGN KEY (Patient_ID) REFERENCES PATIENT(Patient_ID) ON DELETE CASCADE,
    FOREIGN KEY (Doctor_ID)  REFERENCES DOCTOR(Doctor_ID)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS CHAT_SESSION (
    Session_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Patient_ID INTEGER NOT NULL,
    Started_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Patient_ID) REFERENCES PATIENT(Patient_ID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS CHAT_MESSAGE (
    Message_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Session_ID INTEGER NOT NULL,
    Role       TEXT NOT NULL CHECK(Role IN ('user', 'assistant')),
    Content    TEXT NOT NULL,
    Intent     TEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Session_ID) REFERENCES CHAT_SESSION(Session_ID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS SYMPTOM_LOG (
    Log_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
    Patient_ID   INTEGER NOT NULL,
    Symptoms     TEXT NOT NULL,
    Severity     TEXT,
    Is_Escalated INTEGER DEFAULT 0,
    Logged_At    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Patient_ID) REFERENCES PATIENT(Patient_ID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS AUDIT_LOG (
    Audit_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
    Patient_ID INTEGER,
    Action     TEXT NOT NULL,
    Details    TEXT,
    IP_Address TEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Doctor notes on a patient (written from doctor dashboard)
CREATE TABLE IF NOT EXISTS DOCTOR_NOTE (
    Note_ID        INTEGER PRIMARY KEY AUTOINCREMENT,
    Doctor_ID      INTEGER NOT NULL,
    Patient_ID     INTEGER NOT NULL,
    Appointment_ID INTEGER,
    Note           TEXT NOT NULL,
    Created_At     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Doctor_ID)      REFERENCES DOCTOR(Doctor_ID)           ON DELETE CASCADE,
    FOREIGN KEY (Patient_ID)     REFERENCES PATIENT(Patient_ID)         ON DELETE CASCADE,
    FOREIGN KEY (Appointment_ID) REFERENCES APPOINTMENT(Appointment_ID) ON DELETE SET NULL
);
