from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from services import auth_service

router = APIRouter()

class SessionRequest(BaseModel):
    driver_id: str

class SessionResponse(BaseModel):
    session_token: str
    expires_in: int = 900

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    req: SessionRequest,
    authorization: str = Header(None)
):
    """
    [B2B Server-to-Server Endpoint]
    Transport Apps call this endpoint using their Secret API Key to generate
    a secure, short-lived session token for a specific driver.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    api_key = authorization.split(" ")[1]
    
    if api_key != auth_service.MOCK_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    session_token = auth_service.create_session(req.driver_id)
    
    return SessionResponse(session_token=session_token)
