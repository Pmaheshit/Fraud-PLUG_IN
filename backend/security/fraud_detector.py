"""
fraud_detector.py – Suspicious pattern detection and fraud scoring.
Detects:
- Multiple drivers from same device/IP
- High registration failure rates
- Liveness check failures
- Similar face embeddings (duplicate drivers)
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
import aiosqlite
from datetime import datetime, timedelta, timezone
from config import DB_PATH
import numpy as np

logger = logging.getLogger(__name__)


class FraudDetector:
    """Detects suspicious patterns and flags potential fraud."""

    SIMILARITY_THRESHOLD = 0.85  # Cosine similarity threshold for duplicate detection
    MAX_FAILURES_PER_DAY = 5
    MAX_REGISTRATIONS_PER_DEVICE = 3
    FAILURE_WINDOW_HOURS = 24

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    @staticmethod
    async def check_duplicate_drivers(
        embedding: List[float],
        driver_id: str,
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if the face embedding matches existing drivers.
        Detects duplicate/fraudulent registrations.

        Returns:
            (is_duplicate, matching_driver_id, similarity_score)
        """
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT driver_id, face_vector FROM drivers WHERE driver_id != ?",
                (driver_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        max_similarity = 0.0
        matching_driver = None

        for row in rows:
            stored_embedding = json.loads(row["face_vector"])
            similarity = FraudDetector.cosine_similarity(embedding, stored_embedding)

            if similarity > max_similarity:
                max_similarity = similarity
                matching_driver = row["driver_id"]

            if similarity > FraudDetector.SIMILARITY_THRESHOLD:
                logger.warning(
                    f"🚨 DUPLICATE DETECTED | driver={driver_id} | matches={matching_driver} | similarity={similarity:.3f}"
                )
                return True, matching_driver, similarity

        return False, None, max_similarity

    @staticmethod
    async def check_device_overuse(device_fingerprint: str) -> Tuple[bool, int]:
        """
        Check if a device has too many registered drivers.
        Detects bulk/fraudulent registrations from one device.

        Returns:
            (is_suspicious, driver_count)
        """
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM drivers WHERE device_fingerprint = ?",
                (device_fingerprint,),
            ) as cursor:
                row = await cursor.fetchone()
                count = row[0]

        is_suspicious = count >= FraudDetector.MAX_REGISTRATIONS_PER_DEVICE
        return is_suspicious, count

    @staticmethod
    async def check_failure_spike(driver_id: str) -> Tuple[bool, int]:
        """
        Check if a driver has too many failed attempts recently.
        Detects brute force or liveness check bypass attempts.

        Returns:
            (is_suspicious, failure_count)
        """
        cutoff_time = (
            datetime.now(timezone.utc) - timedelta(hours=FraudDetector.FAILURE_WINDOW_HOURS)
        ).isoformat()

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                """
                SELECT COUNT(*) FROM audit_logs
                WHERE driver_id = ? AND status = 'failure' AND timestamp > ?
                """,
                (driver_id, cutoff_time),
            ) as cursor:
                row = await cursor.fetchone()
                failure_count = row[0]

        is_suspicious = failure_count >= FraudDetector.MAX_FAILURES_PER_DAY
        return is_suspicious, failure_count

    @staticmethod
    async def comprehensive_fraud_check(
        driver_id: str,
        device_fingerprint: str,
        face_embedding: List[float],
    ) -> Dict:
        """
        Run comprehensive fraud detection checks.

        Returns:
            {
                "is_fraudulent": bool,
                "risk_score": float (0-1),
                "flags": List[str],
                "details": Dict
            }
        """
        flags = []
        risk_score = 0.0
        details = {}

        # Check for duplicate faces
        is_dup, dup_driver, dup_sim = await FraudDetector.check_duplicate_drivers(
            face_embedding, driver_id
        )
        if is_dup:
            flags.append(f"DUPLICATE_FACE(similarity={dup_sim:.3f},matches={dup_driver})")
            risk_score += 0.4
            details["duplicate"] = {"matching_driver": dup_driver, "similarity": dup_sim}

        # Check for device overuse
        is_overused, dev_count = await FraudDetector.check_device_overuse(device_fingerprint)
        if is_overused:
            flags.append(f"DEVICE_OVERUSE(drivers={dev_count})")
            risk_score += 0.3
            details["device_overuse"] = {"driver_count": dev_count}

        # Check for failure spike
        is_spike, fail_count = await FraudDetector.check_failure_spike(driver_id)
        if is_spike:
            flags.append(f"FAILURE_SPIKE(failures={fail_count})")
            risk_score += 0.3
            details["failure_spike"] = {"failure_count": fail_count}

        is_fraudulent = risk_score >= 0.5

        return {
            "is_fraudulent": is_fraudulent,
            "risk_score": min(risk_score, 1.0),
            "flags": flags,
            "details": details,
        }
