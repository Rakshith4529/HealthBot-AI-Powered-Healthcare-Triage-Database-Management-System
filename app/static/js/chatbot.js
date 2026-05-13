document.addEventListener('DOMContentLoaded', () => {
    const statusDot = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const typingIndicator = document.getElementById('typingIndicator');
    const consentModal = document.getElementById('consentModal');
    const grantConsentBtn = document.getElementById('grantConsentBtn');

    // Check Ollama status
    fetch('/chat/status')
        .then(res => res.json())
        .then(data => {
            if (data.ollama_running) {
                statusDot.className = 'status-dot online';
                statusText.textContent = `Ollama Online (${data.model})`;
            } else {
                statusDot.className = 'status-dot offline';
                statusText.textContent = 'Ollama Offline (Using Fallback)';
            }
        })
        .catch(() => {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Status Check Failed';
        });

    // Handle Consent
    if (grantConsentBtn) {
        grantConsentBtn.addEventListener('click', () => {
            fetch('/chat/consent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    consentModal.style.display = 'none';
                    chatInput.disabled = false;
                    sendBtn.disabled = false;
                    chatInput.focus();
                }
            });
        });
    }

    // Chat functionality
    function addMessage(text, isUser = false) {
        const div = document.createElement('div');
        div.className = `message ${isUser ? 'user-message' : 'system-message'}`;
        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        addMessage(text, true);
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;
        typingIndicator.style.display = 'inline-flex';

        fetch('/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrfToken
            },
            body: JSON.stringify({ message: text })
        })
        .then(res => res.json())
        .then(data => {
            typingIndicator.style.display = 'none';
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();

            if (data.error) {
                addMessage('Error: ' + data.error);
                return;
            }

            let responseMsg = data.message || data.advice;
            if (data.escalated) {
                responseMsg += '\n\n[SEVERITY: ' + data.severity + '] This has been escalated. ';
                if (data.doctors && data.doctors.length > 0) {
                    responseMsg += 'Recommended doctors:\n' + data.doctors.map(d => `- Dr. ${d.First_Name} ${d.Last_Name}`).join('\n');
                }
            }
            addMessage(responseMsg, false);
            
            if (data.requires_confirmation && data.booking_params) {
                const btnDiv = document.createElement('div');
                btnDiv.className = 'message system-message';
                btnDiv.style.backgroundColor = 'transparent';
                btnDiv.style.boxShadow = 'none';
                btnDiv.style.padding = '0';
                
                const btn = document.createElement('button');
                btn.className = 'btn-primary';
                btn.textContent = 'Confirm Booking';
                btn.onclick = () => {
                    chatInput.value = 'confirm_booking ' + JSON.stringify(data.booking_params);
                    sendMessage();
                    btn.disabled = true;
                    btn.textContent = 'Confirming...';
                };
                btnDiv.appendChild(btn);
                chatMessages.appendChild(btnDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        })
        .catch(err => {
            typingIndicator.style.display = 'none';
            chatInput.disabled = false;
            sendBtn.disabled = false;
            addMessage('Failed to connect to the server.');
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});
