from flask import Blueprint, render_template, request, session, jsonify
from app.database import get_db
from app.auth import login_required, get_csrf_token, verify_csrf
from app.ai import agent

chat = Blueprint('chat', __name__)


@chat.route('/chat')
@login_required
def chat_page():
    patient_id = session['patient_id']
    db = get_db()

    # Load or create session
    sess = db.execute(
        "SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID = ? ORDER BY Started_At DESC LIMIT 1",
        (patient_id,)
    ).fetchone()

    history = []
    if sess:
        rows = db.execute("""
            SELECT Role, Content, Intent, Created_At FROM CHAT_MESSAGE
            WHERE Session_ID = ?
            ORDER BY Created_At ASC
            LIMIT 50
        """, (sess['Session_ID'],)).fetchall()
        history = [dict(r) for r in rows]

    return render_template('chat.html', history=history, csrf_token=get_csrf_token())


@chat.route('/chat/message', methods=['POST'])
@login_required
def send_message():
    verify_csrf()
    patient_id = session['patient_id']
    data = request.get_json(silent=True) or {}
    user_text = (data.get('message') or '').strip()

    if not user_text:
        return jsonify({'error': 'Message cannot be empty.'}), 400
    if len(user_text) > 1000:
        return jsonify({'error': 'Message too long (max 1000 characters).'}), 400

    db = get_db()

    # Ensure chat session exists
    sess = db.execute(
        "SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID = ? ORDER BY Started_At DESC LIMIT 1",
        (patient_id,)
    ).fetchone()

    if not sess:
        db.execute("INSERT INTO CHAT_SESSION (Patient_ID) VALUES (?)", (patient_id,))
        db.commit()
        sess = db.execute(
            "SELECT Session_ID FROM CHAT_SESSION WHERE Patient_ID = ? ORDER BY Started_At DESC LIMIT 1",
            (patient_id,)
        ).fetchone()

    session_id = sess['Session_ID']

    # Save user message
    db.execute(
        "INSERT INTO CHAT_MESSAGE (Session_ID, Role, Content) VALUES (?, 'user', ?)",
        (session_id, user_text)
    )
    db.commit()

    # Load history for context
    history = db.execute("""
        SELECT Role, Content, Intent FROM CHAT_MESSAGE
        WHERE Session_ID = ?
        ORDER BY Created_At DESC
        LIMIT 6
    """, (session_id,)).fetchall()
    history = [dict(r) for r in reversed(history)]

    # Process via AI agent
    result = agent.process(patient_id, db, user_text, history=history)

    # Save assistant message
    db.execute(
        "INSERT INTO CHAT_MESSAGE (Session_ID, Role, Content, Intent) VALUES (?, 'assistant', ?, ?)",
        (session_id, result['message'], result['intent'])
    )
    db.commit()

    return jsonify(result)


@chat.route('/chat/status')
def ollama_status():
    from app.ai.ollama import check_ollama
    return jsonify({'online': check_ollama(), 'model': 'llama3'})
