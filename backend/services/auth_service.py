import secrets
import time
from typing import Dict, Optional

# Mock API Key for the dummy Transport App
MOCK_API_KEY = "sk_live_demo123456789"

# In-memory storage for session tokens
# Format: { "sess_token": { "driver_id": "DRV-123", "expires_at": 169... } }
_sessions: Dict[str, dict] = {}

def create_session(driver_id: str) -> str:
    """
    Generate a short-lived session token for a specific driver registration flow.
    Valid for 15 minutes.
    """
    token = f"sess_{secrets.token_urlsafe(16)}"
    _sessions[token] = {
        "driver_id": driver_id,
        "expires_at": time.time() + (15 * 60)
    }
    return token

def validate_and_consume_session(token: str) -> str:
    """
    Validates a session token. If valid, consumes it (so it can't be reused)
    and returns the associated driver_id.
    
    Raises ValueError if invalid or expired.
    """
    if token not in _sessions:
        raise ValueError("Invalid or unrecognized session token.")
    
    session_data = _sessions.pop(token)  # Consume immediately to prevent replay attacks
    
    if time.time() > session_data["expires_at"]:
        raise ValueError("Session token has expired.")
        
    return session_data["driver_id"]
