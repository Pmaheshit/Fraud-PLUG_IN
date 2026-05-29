"""
driver_model.py – Pydantic models for the driver registration domain.

Covers:
  - DriverRegistrationRequest  : incoming POST body
  - DriverRecord               : internal representation / DB row
  - DriverRegistrationResponse : success response payload
  - DriverListItem             : item in the GET /drivers list
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


# ── Inbound ──────────────────────────────────────────────────────────────────

class DriverRegistrationRequest(BaseModel):
    """
    Payload POSTed by the frontend to /api/v1/register-driver.
    """
    driver_id: str = Field(
        ...,
        description="Unique driver identifier (e.g. DRV-001)",
        min_length=1,
        max_length=64,
    )
    device_fingerprint: str = Field(
        ...,
        description="FNV-1a hash of client navigator/screen properties",
        min_length=1,
        max_length=128,
    )
    image_base64: str = Field(
        ...,
        description="Base64-encoded JPEG (data-URI prefix is stripped server-side)",
    )
    liveness_passed: bool = Field(
        False,
        description="Whether the client-side liveness challenge was satisfied",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "driver_id": "DRV-001",
            "device_fingerprint": "a3f9c012",
            "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
            "liveness_passed": True,
        }
    }}


# ── Internal / DB ─────────────────────────────────────────────────────────────

class DriverRecord(BaseModel):
    """
    Full driver record stored in SQLite.
    face_vector is persisted as a JSON string and rehydrated on read.
    """
    driver_id: str
    device_fingerprint: str
    face_vector: List[float]          # 512-D ArcFace embedding
    registered_at: datetime
    embedding_model: str = "insightface_buffalo_l_512d"


# ── Outbound ─────────────────────────────────────────────────────────────────

class DriverRegistrationResponse(BaseModel):
    """
    Response returned after a successful /register-driver call.
    The raw face_vector is intentionally omitted for security.
    """
    status: str
    driver_id: str
    embedding_dimensions: int
    processing_time_ms: float
    registered_at: str
    message: str


class DriverListItem(BaseModel):
    """
    Lightweight summary of a registered driver (no face vector exposed).
    """
    driver_id: str
    device_fingerprint: str
    registered_at: str
    embedding_model: str
    embedding_dimensions: int
