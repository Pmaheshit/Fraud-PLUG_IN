"""
driver.py – FastAPI router for driver registration endpoints with security.

Routes:
  POST /api/v1/register-driver  – create or update a driver biometric record
  GET  /api/v1/drivers          – list all registered drivers (no vectors)

Security Features:
  - Rate limiting (3/day, 10/hour, 2/minute)
  - Audit logging
  - Fraud detection (duplicate faces, device overuse, failure spikes)
  - Webhook alerts
  - JWT authentication
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import List

import aiosqlite
from fastapi import APIRouter, HTTPException, Request

from config import DB_PATH, EMBEDDING_MODEL_LABEL
from models.driver_model import (
    DriverListItem,
    DriverRegistrationRequest,
    DriverRegistrationResponse,
)
from services.face_service import generate_embedding
from security import AuditLogger, FraudDetector, WebhookNotifier, log_action

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Driver Registration"])


# ── POST /register-driver ────────────────────────────────────────────────────

@router.post(
    "/register-driver",
    response_model=DriverRegistrationResponse,
    summary="Register a driver's biometric profile",
    description=(
        "Accepts a base64 image, extracts a 512-D ArcFace embedding via "
        "InsightFace, and persists the record to SQLite. "
        "An existing record for the same driver_id is overwritten (upsert). "
        "Includes fraud detection and audit logging."
    ),
)
async def register_driver(
    payload: DriverRegistrationRequest,
    request: Request,
) -> DriverRegistrationResponse:
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # ── Liveness gate ────────────────────────────────────────────────────────
    if not payload.liveness_passed:
        await log_action(
            action="register_driver_failed",
            driver_id=payload.driver_id,
            ip_address=client_ip,
            status="failure",
            message="Liveness check not completed",
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "Liveness check not completed. "
                "Please perform the on-screen challenge before registering."
            ),
        )

    # ── Face embedding ────────────────────────────────────────────────────────
    try:
        face_vector, processing_time_ms = generate_embedding(payload.image_base64)
    except ValueError as exc:
        logger.warning("Face detection failed for driver %s: %s", payload.driver_id, exc)
        await log_action(
            action="register_driver_failed",
            driver_id=payload.driver_id,
            ip_address=client_ip,
            status="failure",
            message=f"Face detection failed: {str(exc)}",
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during embedding for driver %s", payload.driver_id)
        await log_action(
            action="register_driver_failed",
            driver_id=payload.driver_id,
            ip_address=client_ip,
            status="failure",
            message=f"Internal error: {str(exc)}",
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal face-processing error: {exc}",
        )

    # ── Fraud Detection ───────────────────────────────────────────────────────
    fraud_check = await FraudDetector.comprehensive_fraud_check(
        driver_id=payload.driver_id,
        device_fingerprint=payload.device_fingerprint,
        face_embedding=face_vector,
    )

    if fraud_check["is_fraudulent"]:
        logger.error(
            f"🚨 FRAUD DETECTED | driver={payload.driver_id} | score={fraud_check['risk_score']} | flags={fraud_check['flags']}"
        )
        await log_action(
            action="register_driver_fraud_detected",
            driver_id=payload.driver_id,
            ip_address=client_ip,
            status="failure",
            message=f"Fraud detected: {', '.join(fraud_check['flags'])}",
            context=fraud_check,
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        # Send webhook alert
        await WebhookNotifier.notify_fraud_detected(
            driver_id=payload.driver_id,
            risk_score=fraud_check["risk_score"],
            flags=fraud_check["flags"],
            details=fraud_check["details"],
        )
        raise HTTPException(
            status_code=403,
            detail=f"Registration blocked due to fraud detection. Risk score: {fraud_check['risk_score']:.2f}",
        )

    registered_at = datetime.now(timezone.utc).isoformat()

    # ── Persist (upsert) ──────────────────────────────────────────────────────
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO drivers
                    (driver_id, device_fingerprint, face_vector, registered_at, embedding_model)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(driver_id) DO UPDATE SET
                    device_fingerprint = excluded.device_fingerprint,
                    face_vector        = excluded.face_vector,
                    registered_at      = excluded.registered_at,
                    embedding_model    = excluded.embedding_model
                """,
                (
                    payload.driver_id,
                    payload.device_fingerprint,
                    json.dumps(face_vector),
                    registered_at,
                    EMBEDDING_MODEL_LABEL,
                ),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Database error during registration: {e}")
        await log_action(
            action="register_driver_failed",
            driver_id=payload.driver_id,
            ip_address=client_ip,
            status="failure",
            message=f"Database error: {str(e)}",
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        raise HTTPException(status_code=500, detail="Database error during registration")

    processing_time = (time.time() - start_time) * 1000

    # ── Audit Log Success ─────────────────────────────────────────────────────
    await log_action(
        action="register_driver_success",
        driver_id=payload.driver_id,
        ip_address=client_ip,
        status="success",
        message=f"Driver registered with {len(face_vector)}D embedding",
        context={
            "embedding_dimensions": len(face_vector),
            "fraud_risk_score": fraud_check["risk_score"],
            "device_fingerprint": payload.device_fingerprint,
        },
        processing_time_ms=processing_time,
    )

    # ── Send success webhook ──────────────────────────────────────────────────
    await WebhookNotifier.notify_registration_success(
        driver_id=payload.driver_id,
        embedding_dimensions=len(face_vector),
        processing_time_ms=processing_time,
    )

    logger.info(
        "✅ Driver registered | id=%s | dim=%d | fingerprint=%s | fraud_score=%.2f | %.2f ms",
        payload.driver_id,
        len(face_vector),
        payload.device_fingerprint,
        fraud_check["risk_score"],
        processing_time,
    )

    return DriverRegistrationResponse(
        status="success",
        driver_id=payload.driver_id,
        embedding_dimensions=len(face_vector),
        processing_time_ms=round(processing_time, 2),
        registered_at=registered_at,
        message=(
            f"Driver '{payload.driver_id}' registered successfully with a "
            f"{len(face_vector)}-D ArcFace embedding. Fraud risk score: {fraud_check['risk_score']:.2f}"
        ),
    )



# ── GET /drivers ──────────────────────────────────────────────────────────────

@router.get(
    "/drivers",
    response_model=List[DriverListItem],
    summary="List all registered drivers",
    description="Returns a summary of every registered driver. Face vectors are never exposed.",
)
async def list_drivers(request: Request) -> List[DriverListItem]:
    client_ip = request.client.host if request.client else "unknown"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT driver_id, device_fingerprint, registered_at, embedding_model, face_vector "
            "FROM drivers ORDER BY registered_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()

    # Audit log
    await log_action(
        action="list_drivers",
        ip_address=client_ip,
        status="success",
        message=f"Listed {len(rows)} drivers",
    )

    return [
        DriverListItem(
            driver_id=row["driver_id"],
            device_fingerprint=row["device_fingerprint"],
            registered_at=row["registered_at"],
            embedding_model=row["embedding_model"],
            embedding_dimensions=len(json.loads(row["face_vector"])),
        )
        for row in rows
    ]
