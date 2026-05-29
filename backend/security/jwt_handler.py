"""
jwt_handler.py – JWT token generation and validation.
Replaces simple bearer tokens with stateless JWT tokens containing
claims for driver_id, device_fingerprint, and expiration.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    driver_id: str
    device_fingerprint: Optional[str] = None
    session_id: Optional[str] = None
    exp: datetime
    iat: datetime


class JWTHandler:
    """JWT token creation and validation."""

    ALGORITHM = "HS256"
    TOKEN_EXPIRY_MINUTES = 15

    @staticmethod
    def get_secret_key() -> str:
        """Get the JWT secret key."""
        secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        if secret == "your-secret-key-change-in-production":
            logger.warning("⚠️  Using default JWT secret. Set JWT_SECRET_KEY in production!")
        return secret

    @staticmethod
    def create_token(
        driver_id: str,
        device_fingerprint: Optional[str] = None,
        session_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT token for a driver.

        Args:
            driver_id: Driver identifier
            device_fingerprint: Device fingerprint (optional)
            session_id: Session identifier (optional)
            expires_delta: Custom expiration time

        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWTHandler.TOKEN_EXPIRY_MINUTES)

        expire = now + expires_delta

        payload = {
            "driver_id": driver_id,
            "device_fingerprint": device_fingerprint,
            "session_id": session_id,
            "exp": expire,
            "iat": now,
            "type": "access_token",
        }

        encoded_jwt = jwt.encode(
            payload,
            JWTHandler.get_secret_key(),
            algorithm=JWTHandler.ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                JWTHandler.get_secret_key(),
                algorithms=[JWTHandler.ALGORITHM],
            )
            return payload
        except JWTError as e:
            logger.warning(f"❌ Token verification failed: {e}")
            return None

    @staticmethod
    def extract_driver_id(token: str) -> Optional[str]:
        """Extract driver_id from token."""
        payload = JWTHandler.verify_token(token)
        if payload:
            return payload.get("driver_id")
        return None

    @staticmethod
    def is_token_expired(token: str) -> bool:
        """Check if token is expired."""
        payload = JWTHandler.verify_token(token)
        if not payload:
            return True
        
        exp = payload.get("exp")
        if isinstance(exp, int):
            exp = datetime.fromtimestamp(exp, tz=timezone.utc)
        
        return datetime.now(timezone.utc) > exp
