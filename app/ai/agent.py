"""
Master AI Agent — intent routing via Ollama with rule-based fallback.
"""
import json
import re
from typing import Optional
from flask import current_app
from app.ai.ollama import call_ollama
from app.ai import tools

SYSTEM_PROMPT = """You are MedAssist AI, an intelligent medical assistant chatbot inside a healthcare platform.

Understand the patient's message and respond ONLY with a valid JSON object (no markdown, no extra text):

{
  "intent": "<intent>",
  "params": {},
  "message": "<friendly response>",
  "severity": null,
  "escalate": false
}

CRITICAL:
1. Always analyze the full conversation history to understand pronouns or follow-up references (e.g. "Yes, book it" refers to the appointment discussed previously).
2. For dates, parse natural language like "tomorrow" into actual dates if possible, or extract the provided date directly.

INTENTS and their params:
- "book_appointment"   params: {"doctor_name": "Smith", "date": "YYYY-MM-DD", "time": "HH:MM", "mode": "In-Person|Telemedicine", "specialization": "..."}
- "cancel_appointment" params: {"appointment_id": null, "description": "..."}
- "list_appointments"  params: {}
- "get_medicines"      params: {}
- "find_doctors"       params: {"specialization": "Cardiology|General Practice|Pediatrics|Dermatology|null"}
- "symptom_check"      params: {"symptoms": ["headache", "fever"]}  — also set severity and escalate
- "get_profile"        params: {}
- "general"            params: {}

Severity rules (symptom_check only):
- "CRITICAL" + escalate=true: chest pain, difficulty breathing, severe bleeding, stroke symptoms
- "HIGH"     + escalate=true: fever with other symptoms, persistent severe pain
- "LOW"      + escalate=false: single mild symptom (headache, mild cough, nausea)

Be warm, empathetic, professional. Never definitively diagnose. Respond ONLY with the JSON."""


def _parse(raw: str) -> Optional[dict]:
=======
def _parse(raw: str) -> Optional[dict]:
>>>>>>> a0f31fb (checking)
    if not raw:
        return None
    try:
        text = raw.strip()
        if "```" in text:
            m = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
            text = m.group(1).strip() if m else text
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group()
        data = json.loads(text)
        if 'intent' not in data or 'message' not in data:
            return None
        data.setdefault('params', {})
        data.setdefault('severity', None)
        data.setdefault('escalate', False)
        return data
    except Exception as e:
        current_app.logger.warning(f"Agent parse failed: {e} | raw: {raw[:200]}")
        return None


def _extract_booking_params(t: str, original: str = '') -> dict:
    """Extract doctor name, date, time, mode from natural language."""
    params = {}

    # Date: YYYY-MM-DD
    from datetime import datetime, timedelta
    
    m = re.search(r'(\d{4}-\d{2}-\d{2})', t)
    if m:
        params['date'] = m.group(1)
    elif 'tomorrow' in t:
        params['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in t:
        params['date'] = datetime.now().strftime('%Y-%m-%d')
    else:
        # Try June 10, 2026 / 10 June 2026 / tomorrow etc.
        months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                  'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
        m2 = re.search(r'(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*,?\s*(\d{4})?', t)
        if m2:
            day, mon, yr = m2.group(1), m2.group(2), m2.group(3) or str(datetime.now().year)
            params['date'] = f"{int(yr):04d}-{months[mon]:02d}-{int(day):02d}"
        else:
            m3 = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s*(\d{4})?', t)
            if m3:
                mon, day, yr = m3.group(1), m3.group(2), m3.group(3) or str(datetime.now().year)
                params['date'] = f"{int(yr):04d}-{months[mon]:02d}-{int(day):02d}"

    # Time: HH:MM or H am/pm
    mt = re.search(r'(\d{1,2}):(\d{2})', t)
    if mt:
        params['time'] = f"{int(mt.group(1)):02d}:{mt.group(2)}"
    else:
        mt2 = re.search(r'at\s+(\d{1,2})\s*(am|pm)', t)
        if mt2:
            h = int(mt2.group(1))
            if mt2.group(2) == 'pm' and h < 12:
                h += 12
            elif mt2.group(2) == 'am' and h == 12:
                h = 0
            params['time'] = f"{h:02d}:00"
        else:
            mt3 = re.search(r'(\d{1,2})\s*pm', t)
            if mt3:
                h = int(mt3.group(1))
                if h < 12: h += 12
                params['time'] = f"{h:02d}:00"
            else:
                mt4 = re.search(r'(\d{1,2})\s*am', t)
                if mt4:
                    h = int(mt4.group(1))
                    if h == 12: h = 0
                    params['time'] = f"{h:02d}:00"

    # Doctor name: "Dr. Carter" / "dr carter" / "Dr Thompson"
    md = re.search(r'dr\.?\s+([a-z]+)', t)
    if md:
        params['doctor_name'] = md.group(1).title()

    # Mode
    if 'tele' in t or 'video' in t or 'online' in t or 'virtual' in t or 'remote' in t:
        params['mode'] = 'Telemedicine'
    else:
        params['mode'] = 'In-Person'

    # Specialization fallback
    spec_map = {'cardiolog': 'Cardiology', 'heart': 'Cardiology', 'general': 'General Practice',
                'gp': 'General Practice', 'pediatr': 'Pediatrics', 'child': 'Pediatrics',
                'dermatol': 'Dermatology', 'skin': 'Dermatology', 'orthop': 'Orthopedics',
                'neurol': 'Neurology', 'brain': 'Neurology'}
    for kw, spec in spec_map.items():
        if kw in t:
            params.setdefault('specialization', spec)
            break

    return params


def _fallback(text: str) -> dict:
    """Keyword-based intent routing when Ollama is unavailable."""
    t = text.lower()

    # Emergency
    if any(w in t for w in ['chest pain', 'difficulty breathing', 'can\'t breathe', 'severe bleeding', 'heart attack', 'stroke']):
        return {"intent": "symptom_check", "params": {"symptoms": ["chest pain"]},
                "message": "🚨 **Emergency detected.** Please call **911** or go to your nearest emergency room immediately. Do not wait.",
                "severity": "CRITICAL", "escalate": True}

    if ('book' in t or 'schedule' in t or 'make' in t or 'set up' in t) and \
       ('appointment' in t or 'doctor' in t or 'visit' in t or 'dr.' in t or 'dr ' in t):
        bparams = _extract_booking_params(t, text)
        if bparams.get('date') and (bparams.get('doctor_name') or bparams.get('specialization')):
            return {"intent": "book_appointment", "params": bparams,
                    "message": "Let me prepare that booking for you.", "severity": None, "escalate": False}
        return {"intent": "book_appointment", "params": bparams,
                "message": "I'll help you book an appointment. Which doctor or specialty do you need, and what date works for you?",
                "severity": None, "escalate": False}

    if 'cancel' in t and ('appointment' in t or 'booking' in t):
        return {"intent": "cancel_appointment", "params": {},
                "message": "I can cancel your appointment. I'll cancel your next scheduled appointment — is that correct?",
                "severity": None, "escalate": False}

    if any(w in t for w in ['my appointment', 'appointments', 'upcoming', 'scheduled', 'booking']):
        return {"intent": "list_appointments", "params": {},
                "message": "Here are your appointments:", "severity": None, "escalate": False}

    if any(w in t for w in ['medicine', 'medication', 'prescription', 'drug', 'pill', 'tablet']):
        return {"intent": "get_medicines", "params": {},
                "message": "Here are your current prescriptions:", "severity": None, "escalate": False}

    if any(w in t for w in ['find doctor', 'show doctor', 'list doctor', 'available doctor', 'specialist']):
        return {"intent": "find_doctors", "params": {},
                "message": "Here are our available doctors:", "severity": None, "escalate": False}

    if 'my profile' in t or 'my info' in t or 'my details' in t or 'my account' in t:
        return {"intent": "get_profile", "params": {},
                "message": "Here is your profile:", "severity": None, "escalate": False}

    # Symptom detection
    symptom_map = {
        'fever': 'Fever', 'headache': 'Headache', 'head ache': 'Headache',
        'cough': 'Cough', 'nausea': 'Nausea', 'vomit': 'Nausea',
        'pain': 'Pain', 'fatigue': 'Fatigue', 'tired': 'Fatigue',
        'dizziness': 'Dizziness', 'dizzy': 'Dizziness',
        'rash': 'Rash', 'sore throat': 'Sore Throat',
    }
    found = [v for k, v in symptom_map.items() if k in t]
    if found:
        severity = "LOW"
        escalate = False
        advice_parts = {
            'Fever': 'Take paracetamol, rest, and stay hydrated. See a doctor if fever exceeds 39°C or lasts >3 days.',
            'Headache': 'Rest in a quiet room. Ibuprofen or paracetamol may help. Stay hydrated.',
            'Cough': 'Try honey with warm water. Avoid irritants. See a doctor if it persists >2 weeks.',
            'Nausea': 'Eat small bland meals. Sip water slowly. Ginger tea may help.',
            'Pain': 'Rest the area. OTC pain relievers may help. Seek care if severe or worsening.',
            'Fatigue': 'Ensure adequate sleep, hydration, and nutrition.',
            'Dizziness': 'Sit or lie down immediately. Stay hydrated. Avoid sudden movements.',
            'Rash': 'Avoid scratching. Apply calamine lotion. See a doctor if spreading or painful.',
            'Sore Throat': 'Gargle warm salt water. Throat lozenges may help. See a doctor if very painful.',
        }
        if len(found) > 2 or ('Fever' in found and len(found) > 1):
            severity, escalate = "HIGH", True

        advice = ' '.join([advice_parts.get(s, '') for s in found])
        return {"intent": "symptom_check", "params": {"symptoms": found},
                "message": advice, "severity": severity, "escalate": escalate}

    return {"intent": "general", "params": {},
            "message": "👋 Hi! I'm **MedAssist AI**. I can help you:\n- 📅 Book or cancel appointments\n- 💊 View your prescriptions\n- 🩺 Check symptoms and get advice\n- 🔍 Find doctors\n\nWhat would you like to do today?",
            "severity": None, "escalate": False}


def process(patient_id: int, db, user_text: str, history: list = None) -> dict:
    """Main agent pipeline: Ollama → fallback → tools dispatch."""
    # Try Ollama
    raw = call_ollama(user_text, system=SYSTEM_PROMPT, history=history)
    agent_data = _parse(raw) if raw else None

    if not agent_data:
        # Check explicit button clicks FIRST, using JUST user_text (not context_text)
        if user_text.startswith('confirm_booking'):
            try:
                params_str = user_text.replace('confirm_booking ', '')
                params = json.loads(params_str)
                agent_data = {"intent": "confirm_booking", "params": params, "message": "Processing..."}
            except Exception as e:
                current_app.logger.error("Failed to parse confirm_booking: " + str(e))
                agent_data = None
                
        if not agent_data:
            # Pass full context string to fallback for better date extraction
            context_text = user_text
            last_intent = None
            if history:
                context_text = " ".join([h['Content'] for h in history[-2:]]) + " " + user_text
                for h in reversed(history):
                    if h.get('Role') == 'assistant':
                        last_intent = h.get('Intent')
                        break
                
            ut = user_text.lower().strip()
            
            # Intercept simple confirmations or cancellations
            if last_intent == 'book_appointment' and ut in ['yes', 'y', 'confirm', 'sure', 'ok', 'do it', 'book it', 'please', 'yeah', 'yep']:
                bparams = _extract_booking_params(context_text.lower(), context_text)
                agent_data = {"intent": "confirm_booking", "params": bparams}
            elif last_intent == 'book_appointment' and ut in ['no', 'n', 'cancel', 'stop', 'nope']:
                agent_data = {"intent": "general", "message": "Okay, I've cancelled the booking process. How else can I help you?"}
            else:
                agent_data = _fallback(context_text)
                
                # If the last intent was booking and we didn't match a new strong intent, assume continued booking
                if last_intent == 'book_appointment' and agent_data.get('intent') == 'general':
                    # Extract params from the user text
                    bparams = _extract_booking_params(context_text.lower(), context_text)
                    agent_data = {"intent": "book_appointment", "params": bparams, "message": "Booking..."}
                
            current_app.logger.info("Using fallback rule engine")

    intent = agent_data.get('intent', 'general')
    params = agent_data.get('params', {})
    result = {}

    try:
        if intent == 'list_appointments':
            result = tools.list_appointments(patient_id, db)
        elif intent == 'book_appointment':
            # Instead of booking, require confirmation
            agent_data['requires_confirmation'] = True
            agent_data['booking_params'] = params
            
            doctor_text = params.get('doctor_name') or params.get('specialization') or "a doctor"
            date_text = params.get('date', '')
            time_text = params.get('time', '')
            mode_text = params.get('mode', 'In-Person')
            
            if date_text and time_text:
                agent_data['message'] = f"Please confirm you want to book an {mode_text} appointment with {doctor_text} on {date_text} at {time_text}."
            else:
                agent_data['message'] = f"I'm preparing to book an appointment with {doctor_text}. Could you please provide a preferred date and time?"
                agent_data['requires_confirmation'] = False # Not ready to confirm yet
                
        elif intent == 'confirm_booking':
            result = tools.book_appointment(patient_id, db, params)
            if result.get('success'):
                agent_data['message'] = f"✅ Appointment booked successfully {result.get('detail', '')}!"
            elif result.get('error'):
                agent_data['message'] = f"❌ {result['error']}"
        elif intent == 'cancel_appointment':
            result = tools.cancel_appointment(patient_id, db, params)
            if result.get('success'):
                agent_data['message'] = "✅ Your appointment has been cancelled successfully."
            elif result.get('error'):
                agent_data['message'] = f"❌ {result['error']}"
        elif intent == 'get_medicines':
            result = tools.get_medicines(patient_id, db)
        elif intent == 'find_doctors':
            result = tools.find_doctors(db, params)
        elif intent == 'symptom_check':
            result = tools.log_symptom(patient_id, db, params,
                                       agent_data.get('severity'), agent_data.get('escalate'))
            if agent_data.get('escalate'):
                spec = params.get('specialization') or _map_severity_to_spec(params.get('symptoms', []))
                docs = tools.find_doctors(db, {'specialization': spec})
                result['recommended_doctors'] = docs.get('doctors', [])[:3]
        elif intent == 'get_profile':
            result = tools.get_profile(patient_id, db)
    except Exception as e:
        current_app.logger.error(f"Tool error [{intent}]: {e}")
        result = {'error': str(e)}

    return {
        "message": agent_data.get('message', "I'm here to help. What can I do for you?"),
        "intent": intent,
        "data": result,
        "requires_confirmation": agent_data.get('requires_confirmation', False),
        "booking_params": agent_data.get('booking_params', {}),
        "severity": agent_data.get('severity'),
        "escalate": agent_data.get('escalate', False),
    }


def _map_severity_to_spec(symptoms: list) -> str:
    s = [x.lower() for x in symptoms]
    if any(w in s for w in ['chest pain', 'heart']):
        return 'Cardiology'
    if any(w in s for w in ['rash', 'skin']):
        return 'Dermatology'
    return 'General Practice'
