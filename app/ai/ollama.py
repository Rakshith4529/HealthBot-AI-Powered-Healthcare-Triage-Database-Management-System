import json
import urllib.request
import urllib.error
from flask import current_app


def call_ollama(prompt: str, system: str = None, history: list = None, timeout: int = 25) -> str | None:
    """Call local Ollama. Returns response text or None on failure."""
    url = f"{current_app.config['OLLAMA_URL']}/api/generate"
    model = current_app.config['OLLAMA_MODEL']
    
    # Build text prompt
    full_prompt = f"{system}\n\n" if system else ""
    if history:
        for msg in history[-4:]: # Use last 4 messages for context
            role = "User" if msg['Role'] == 'user' else "Assistant"
            full_prompt += f"{role}: {msg['Content']}\n"
            
    full_prompt += f"User: {prompt}\nAssistant: "

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 600},
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")
    except Exception as e:
        current_app.logger.warning(f"Ollama unavailable: {e}")
        return None


def check_ollama() -> bool:
    """Quick health check for Ollama server."""
    try:
        url = current_app.config['OLLAMA_URL'] + "/api/tags"
        with urllib.request.urlopen(url, timeout=3):
            return True
    except Exception:
        return False
