"""
audit_logger.py – Comprehensive audit logging for all API actions.
Logs every registration, verification, session, and system event with
timestamp, actor, action, status, and context.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import aiosqlite
from config import DB_PATH

logger = logging.getLogger(__name__)


class AuditLogger:
    """Centralized audit logging service."""

    @staticmethod
    async def init_audit_table() -> None:
        """Create audit log table if it doesn't exist."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    driver_id TEXT,
                    ip_address TEXT,
                    status TEXT,
                    message TEXT,
                    context TEXT,
                    processing_time_ms REAL
                )
                """
            )
            await db.commit()
        logger.info("✅ Audit log table ready")

    @staticmethod
    async def log(
        action: str,
        driver_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
        message: str = "",
        context: Optional[Dict[str, Any]] = None,
        processing_time_ms: float = 0.0,
    ) -> None:
        """
        Log an action to the audit table.

        Args:
            action: Type of action (register, verify, session_create, etc.)
            driver_id: Associated driver ID (optional)
            ip_address: Client IP address
            status: success/failure/warning
            message: Detailed message
            context: Additional JSON context
            processing_time_ms: Time taken for the action
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        context_json = json.dumps(context) if context else None

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO audit_logs
                    (timestamp, action, driver_id, ip_address, status, message, context, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        action,
                        driver_id,
                        ip_address,
                        status,
                        message,
                        context_json,
                        processing_time_ms,
                    ),
                )
                await db.commit()

            logger.info(
                f"📋 AUDIT | action={action} | driver={driver_id} | status={status} | ip={ip_address}"
            )
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    @staticmethod
    async def get_driver_logs(driver_id: str, limit: int = 50) -> list:
        """Get all audit logs for a specific driver."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audit_logs WHERE driver_id = ? ORDER BY timestamp DESC LIMIT ?",
                (driver_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


async def log_action(
    action: str,
    driver_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
    message: str = "",
    context: Optional[Dict[str, Any]] = None,
    processing_time_ms: float = 0.0,
) -> None:
    """Convenience function to log actions."""
    await AuditLogger.log(
        action=action,
        driver_id=driver_id,
        ip_address=ip_address,
        status=status,
        message=message,
        context=context,
        processing_time_ms=processing_time_ms,
    )
