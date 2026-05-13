# MedAssist - Healthcare Management System

A production-ready Flask web application for patient-facing healthcare management. Built with Flask 3.x, SQLite3, and vanilla HTML5/CSS3/JavaScript.

## 🚀 Features

- **User Authentication**: Secure login/registration with role-based access (Patient, Doctor, Admin)
- **Patient Management**: Profile management, medical history, and health information
- **Doctor Directory**: Search and filter doctors by specialization
- **Appointment System**: Book, rate, and manage medical appointments
- **Medical Records**: Store and retrieve patient medical records
- **Chat Assistance**: AI-powered healthcare chatbot for patient support
- **Admin Panel**: User management, audit logs, and system monitoring
- **Security**: Parameterized SQL queries, password hashing, CSRF protection

## 📋 Technology Stack

- **Backend**: Python 3.11+, Flask 3.x
- **Database**: SQLite3 (built-in Python module)
- **Frontend**: Jinja2, HTML5, CSS3, ES6+ JavaScript
- **Security**: Werkzeug (password hashing), parameterized queries

## 📁 Project Structure

```
medassist/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration (Dev/Prod/Testing)
│   ├── database.py              # Database connection manager
│   ├── blueprints/
│   │   ├── auth.py              # Authentication routes
│   │   ├── patient.py           # Patient dashboard & profile
│   │   ├── doctor.py            # Doctor directory
│   │   ├── appointment.py       # Appointment booking
│   │   ├── chatbot.py           # Chat interface
│   │   └── admin.py             # Admin panel
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/                # Login, register
│   │   ├── patient/             # Dashboard, profile, appointments
│   │   ├── doctor/              # Directory, profiles
│   │   ├── appointment/         # Booking interface
│   │   ├── chatbot/             # Chat interface
│   │   └── admin/               # Admin pages
│   └── static/
│       ├── css/main.css         # Main stylesheet
│       └── js/
│           ├── main.js          # Shared utilities
│           └── chatbot.js       # Chatbot interface
├── schema.sql                   # Database schema
├── seed.sql                     # Sample data
├── run.py                       # Application entry point
└── requirements.txt             # Python dependencies
```

## 🔧 Installation & Setup

### 1. Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### 2. Install Dependencies

```bash
cd medassist
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
flask --app run init-db
```

This creates the database schema and tables.

### 4. Seed Sample Data (Optional)

```bash
flask --app run seed-db
```

This populates the database with demo users and data.

### 5. Run Development Server

```bash
python run.py
```

The application will start at `http://127.0.0.1:5000`

## 👤 Demo Credentials

After seeding the database, use these credentials to test:

| Role | Email | Password |
|------|-------|----------|
| Patient | patient1@example.com | Patient@123 |
| Doctor | doctor1@medassist.local | Doctor@123 |
| Admin | admin@medassist.local | Admin@123 |

## 📚 API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/verify-session` - Check authentication status

### Patient Routes
- `GET /patient/dashboard` - Patient dashboard
- `GET /patient/profile` - View/edit profile
- `POST /patient/profile` - Update profile
- `GET /patient/appointments` - View appointments
- `GET /patient/medical-records` - View medical records
- `GET /patient/api/appointments` - API endpoint for appointments

### Doctor Routes
- `GET /doctor/directory` - Browse doctors
- `GET /doctor/profile/<id>` - View doctor profile
- `GET /doctor/api/doctors` - API: Get doctors list
- `GET /doctor/api/specializations` - API: Get specializations

### Appointment Routes
- `GET /appointment/book` - Booking form
- `POST /appointment/book` - Create appointment
- `GET /appointment/api/availability` - Check doctor availability
- `POST /appointment/<id>/cancel` - Cancel appointment
- `POST /appointment/<id>/rate` - Rate appointment

### Chat Routes
- `GET /chat/interface` - Chat interface
- `POST /chat/api/session/create` - Create chat session
- `POST /chat/api/session/<id>/message` - Send message
- `GET /chat/api/session/<id>/messages` - Get conversation
- `GET /chat/api/sessions` - Get user sessions

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - Manage users
- `POST /admin/users/<id>/toggle-active` - Activate/deactivate user
- `GET /admin/audit-logs` - View audit logs
- `GET /admin/appointments` - View all appointments
- `GET /admin/api/statistics` - API: System statistics

## 🔐 Security Features

1. **Password Hashing**: All passwords hashed with Werkzeug's PBKDF2
2. **Parameterized Queries**: All SQL queries use parameter binding to prevent SQL injection
3. **Session Management**: Secure session cookies with HTTP-only flag
4. **Role-Based Access**: Decorators enforce access control
5. **CSRF Protection**: Request validation via session management
6. **Foreign Keys**: Database-level referential integrity

## 🛠️ Configuration

### Development vs Production

Environment variables:
```bash
FLASK_ENV=development      # development, production, testing
SECRET_KEY=your-secret-key  # Set in production!
```

Configuration files in `app/config.py`:
- `DevelopmentConfig`: Debug enabled, relaxed security
- `ProductionConfig`: Debug disabled, secure cookies
- `TestingConfig`: In-memory database, testing optimizations

## 📦 Database Schema Highlights

- **users**: User accounts (patients, doctors, admins)
- **appointments**: Booking system with ratings
- **medical_records**: Patient medical history
- **doctor_availability**: Doctor schedule
- **chat_sessions**: Chat conversation sessions
- **chat_messages**: Individual messages
- **audit_logs**: System activity tracking

## 🚀 Deployment

### Production Checklist

1. Set `FLASK_ENV=production`
2. Generate a strong `SECRET_KEY`
3. Use a production WSGI server (Gunicorn, uWSGI)
4. Enable HTTPS/SSL
5. Configure a production database
6. Set up proper logging
7. Configure environment variables

### Example Production Run (Gunicorn)

```bash
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5000 --env FLASK_ENV=production run:app
```

## 📖 Usage Examples

### Register a New User

```python
# POST /auth/register
{
    "email": "user@example.com",
    "password": "SecurePassword123",
    "confirm_password": "SecurePassword123",
    "full_name": "John Doe",
    "user_type": "patient"
}
```

### Book an Appointment

```python
# POST /appointment/book
{
    "doctor_id": 1,
    "appointment_date": "2024-05-20",
    "appointment_time": "14:00",
    "reason": "Regular checkup"
}
```

### Send Chat Message

```python
# POST /chat/api/session/1/message
{
    "message": "I have a headache"
}
```

## 🧪 Testing

Run tests:
```bash
python -m pytest
```

Create a test database:
```bash
FLASK_ENV=testing flask --app run init-db
```

## 📝 CLI Commands

```bash
# Initialize database
flask --app run init-db

# Seed sample data
flask --app run seed-db

# Initialize and seed fresh database
flask --app run seed-fresh

# Run development server
python run.py
```

## 🤝 Contributing

This is a production-ready template. Extensions can include:

1. **AI Integration**: Replace chatbot placeholder with OpenAI API
2. **Notifications**: Email/SMS notifications for appointments
3. **Video Consultations**: Integrate WebRTC for telemedicine
4. **Payment Processing**: Stripe integration for billing
5. **Mobile App**: React Native or Flutter frontend
6. **Analytics**: Dashboard analytics and reporting

## 📄 License

This project is provided as-is for educational and commercial use.

## 🆘 Support

For issues or questions:
1. Check database schema in `schema.sql`
2. Review error logs in console
3. Verify configuration in `app/config.py`
4. Check database initialization with `flask --app run init-db`

## 🎯 Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Initialize database: `flask --app run init-db`
3. Seed sample data: `flask --app run seed-db`
4. Start server: `python run.py`
5. Open `http://127.0.0.1:5000` in browser
6. Login with demo credentials

---

Built with ❤️ as a production-ready healthcare management system.
