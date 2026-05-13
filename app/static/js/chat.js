/* chat.js — MedAssist AI Chat Interface */
const messagesEl = document.getElementById('chat-messages');
const inputEl    = document.getElementById('chat-input');
const sendBtn    = document.getElementById('chat-send-btn');
const typingEl   = document.getElementById('typing-indicator');

// Auto-send from quick-action links (?q=...)
window.addEventListener('DOMContentLoaded', () => {
  checkOllama();
  if (INITIAL_Q) {
    inputEl.value = decodeURIComponent(INITIAL_Q);
    setTimeout(sendMessage, 400);
  }
  // Auto-resize textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 150) + 'px';
  });
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  scrollBottom();
});

function checkOllama() {
  fetch('/chat/status').then(r => r.json()).then(d => {
    const dot   = document.getElementById('ollama-dot');
    const label = document.getElementById('ollama-label');
    if (d.online) {
      dot.classList.add('online');
      label.textContent = 'AI Online';
    } else {
      dot.classList.add('offline');
      label.textContent = 'Fallback Mode';
    }
  }).catch(() => {});
}

function sendChip(btn) {
  inputEl.value = btn.textContent.replace(/^[^\w]+/, '').trim();
  sendMessage();
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  // Render user message
  appendMessage('user', text);
  scrollBottom();

  // Show typing
  typingEl.style.display = 'flex';
  scrollBottom();

  try {
    const res = await fetch('/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF_TOKEN },
      body: JSON.stringify({ message: text, csrf_token: CSRF_TOKEN }),
    });
    const data = await res.json();
    typingEl.style.display = 'none';

    if (!res.ok) {
      appendMessage('bot', `❌ ${data.error || 'Something went wrong.'}`);
    } else {
      renderBotResponse(data);
    }
  } catch (err) {
    typingEl.style.display = 'none';
    appendMessage('bot', '❌ Network error. Please check your connection.');
  }

  sendBtn.disabled = false;
  scrollBottom();
  // Hide suggestions after first message
  const chips = document.getElementById('chat-suggestions');
  if (chips) chips.style.display = 'none';
}

function appendMessage(role, text) {
  const isUser = role === 'user';
  const row = document.createElement('div');
  row.className = `msg-row ${isUser ? 'msg-user' : 'msg-bot'}`;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar ${isUser ? 'msg-avatar-user' : ''}`;
  avatar.textContent = isUser ? 'You' : '✚';

  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${isUser ? 'msg-bubble-user' : 'msg-bubble-bot'}`;
  bubble.innerHTML = formatText(text);

  const time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  bubble.appendChild(time);

  if (isUser) { row.appendChild(bubble); row.appendChild(avatar); }
  else         { row.appendChild(avatar); row.appendChild(bubble); }

  messagesEl.insertBefore(row, typingEl);
}

function renderBotResponse(data) {
  const row    = document.createElement('div');
  row.className = 'msg-row msg-bot';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = '✚';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble msg-bubble-bot';

  // Severity badge
  if (data.severity) {
    const badge = document.createElement('div');
    badge.className = `severity-badge sev-${data.severity}`;
    badge.innerHTML = `${data.severity === 'CRITICAL' ? '🚨' : data.severity === 'HIGH' ? '⚠️' : '✅'} ${data.severity} Severity`;
    bubble.appendChild(badge);
  }

  // Main message
  const msgDiv = document.createElement('div');
  msgDiv.innerHTML = formatText(data.message);
  bubble.appendChild(msgDiv);

  // Intent-specific cards
  const d = data.data || {};

  if (data.intent === 'list_appointments' && d.appointments) {
    bubble.appendChild(buildAppointmentCard(d.appointments));
  }
  if (data.intent === 'get_medicines' && d.prescriptions) {
    bubble.appendChild(buildMedCard(d.prescriptions));
  }
  if ((data.intent === 'find_doctors' && d.doctors) ||
      (data.intent === 'symptom_check' && d.recommended_doctors)) {
    const docs = d.doctors || d.recommended_doctors || [];
    if (docs.length) bubble.appendChild(buildDoctorCard(docs));
  }
  if (data.intent === 'get_profile' && d.profile) {
    bubble.appendChild(buildProfileCard(d.profile));
  }
  if (data.intent === 'book_appointment' && d.doctor) {
    bubble.appendChild(buildBookingConfirmCard(d));
  }

  const time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  bubble.appendChild(time);

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.insertBefore(row, typingEl);
}

function buildAppointmentCard(appts) {
  const card = document.createElement('div');
  card.className = 'chat-card';
  card.innerHTML = `<div class="chat-card-title">📅 Your Appointments</div>`;
  if (!appts.length) { card.innerHTML += '<p style="color:var(--text-m);font-size:.875rem">No appointments found.</p>'; return card; }
  appts.forEach(a => {
    const row = document.createElement('div');
    row.className = 'appt-card-row';
    row.innerHTML = `
      <div class="appt-avatar">${(a.Doctor_Name||'?')[0]}</div>
      <div style="flex:1">
        <div style="font-weight:600;font-size:.875rem">Dr. ${a.Doctor_Name||''}</div>
        <div style="font-size:.78rem;color:var(--teal)">${a.Specialization||''}</div>
        <div style="font-size:.78rem;color:var(--text-m)">${(a.Scheduled_At||'').slice(0,16)}</div>
      </div>
      <div>
        <span class="badge badge-${(a.Mode||'').toLowerCase().includes('tele')?'tele':'in'}">${a.Mode||''}</span><br/>
        <span class="badge badge-${(a.Status||'').toLowerCase()}">${a.Status||''}</span>
      </div>`;
    card.appendChild(row);
  });
  return card;
}

function buildMedCard(rxs) {
  const card = document.createElement('div');
  card.className = 'chat-card';
  card.innerHTML = `<div class="chat-card-title">💊 Your Prescriptions</div>`;
  if (!rxs.length) { card.innerHTML += '<p style="color:var(--text-m);font-size:.875rem">No prescriptions found.</p>'; return card; }
  rxs.forEach(r => {
    const row = document.createElement('div');
    row.className = 'med-row';
    row.innerHTML = `
      <div class="med-icon">💊</div>
      <div style="flex:1">
        <div class="med-name">${r.Medicine_Name||''}</div>
        <div class="med-dose">${r.Dosage_Instructions||''}</div>
        <div style="font-size:.75rem;color:var(--text-d)">Prescribed by Dr. ${r.Doctor_Name||'N/A'} · ${(r.Prescribed_At||'').slice(0,10)}</div>
      </div>
      ${r.Duration_Days ? `<span style="font-size:.78rem;color:var(--teal)">${r.Duration_Days}d</span>` : ''}`;
    card.appendChild(row);
  });
  return card;
}

function buildDoctorCard(docs) {
  const card = document.createElement('div');
  card.className = 'chat-card';
  card.innerHTML = `<div class="chat-card-title">🩺 Available Doctors</div>`;
  docs.slice(0, 4).forEach(d => {
    const row = document.createElement('div');
    row.className = 'doctor-card';
    row.innerHTML = `
      <div class="doctor-av">${(d.Name||'?')[0]}</div>
      <div class="doctor-info">
        <div class="doctor-name">Dr. ${d.Name||''}</div>
        <div class="doctor-spec">${d.Specialization||''}</div>
        <div class="doctor-exp">${d.Experience_Years||0} years experience</div>
      </div>
      <div class="doctor-rating">⭐ ${d.Rating||'4.5'}</div>`;
    card.appendChild(row);
  });
  const bookBtn = document.createElement('button');
  bookBtn.className = 'btn-primary btn-full';
  bookBtn.style.marginTop = '.75rem';
  bookBtn.style.fontSize = '.85rem';
  bookBtn.textContent = '📅 Book an Appointment';
  bookBtn.onclick = () => { inputEl.value = 'Book an appointment'; sendMessage(); };
  card.appendChild(bookBtn);
  return card;
}

function buildProfileCard(p) {
  const card = document.createElement('div');
  card.className = 'chat-card';
  card.innerHTML = `
    <div class="chat-card-title">👤 Your Profile</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;font-size:.875rem">
      <div><span style="color:var(--text-m)">Name:</span> ${p.First_Name||''} ${p.Last_Name||''}</div>
      <div><span style="color:var(--text-m)">Email:</span> ${p.Email||''}</div>
      <div><span style="color:var(--text-m)">DOB:</span> ${p.DOB||'N/A'}</div>
      <div><span style="color:var(--text-m)">Gender:</span> ${p.Gender||'N/A'}</div>
    </div>`;
  return card;
}

function buildBookingConfirmCard(d) {
  if (!d.success) return document.createElement('span');
  const card = document.createElement('div');
  card.className = 'chat-card';
  card.innerHTML = `
    <div class="chat-card-title" style="color:#34d399">✅ Appointment Confirmed</div>
    <div style="font-size:.875rem">
      <strong>Dr. ${d.doctor?.Name||''}</strong> · ${d.doctor?.Specialization||''}<br/>
      <span style="color:var(--text-m)">${d.scheduled_at||''} · ${d.mode||''}</span>
    </div>`;
  return card;
}

function formatText(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/🚨|⚠️|✅|📅|💊|🩺|🔍|👤|💬|🤒|📋/g, '<span>$&</span>')
    .replace(/\n/g, '<br/>');
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
