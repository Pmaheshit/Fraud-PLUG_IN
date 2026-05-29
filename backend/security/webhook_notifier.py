"""
webhook_notifier.py – Webhook notifications for suspicious activities.
Sends real-time alerts to configured webhooks when fraud is detected.
"""
import json
import logging
import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Sends webhook notifications for security events."""

    @staticmethod
    def get_webhook_urls() -> Dict[str, str]:
        """Get configured webhook URLs from environment."""
        return {
            "fraud": os.getenv("WEBHOOK_FRAUD_URL", ""),
            "registration": os.getenv("WEBHOOK_REGISTRATION_URL", ""),
            "alert": os.getenv("WEBHOOK_ALERT_URL", ""),
        }

    @staticmethod
    async def notify_fraud_detected(
        driver_id: str,
        risk_score: float,
        flags: list,
        details: Dict[str, Any],
    ) -> bool:
        """
        Send fraud alert webhook.

        Args:
            driver_id: Fraudulent driver ID
            risk_score: Risk score (0-1)
            flags: List of fraud flags
            details: Detailed fraud info

        Returns:
            True if webhook sent successfully
        """
        webhook_url = WebhookNotifier.get_webhook_urls().get("fraud")
        if not webhook_url:
            logger.debug("No fraud webhook URL configured")
            return False

        payload = {
            "event": "fraud_detected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "driver_id": driver_id,
            "risk_score": risk_score,
            "flags": flags,
            "details": details,
            "severity": "HIGH" if risk_score >= 0.75 else "MEDIUM",
        }

        return await WebhookNotifier._send_webhook(webhook_url, payload, "fraud_detection")

    @staticmethod
    async def notify_duplicate_driver(
        driver_id: str,
        matching_driver: str,
        similarity: float,
    ) -> bool:
        """Send notification for duplicate driver detection."""
        webhook_url = WebhookNotifier.get_webhook_urls().get("alert")
        if not webhook_url:
            return False

        payload = {
            "event": "duplicate_driver_detected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "driver_id": driver_id,
            "matching_driver": matching_driver,
            "similarity": similarity,
            "action_required": True,
        }

        return await WebhookNotifier._send_webhook(webhook_url, payload, "duplicate_detection")

    @staticmethod
    async def notify_registration_success(
        driver_id: str,
        embedding_dimensions: int,
        processing_time_ms: float,
    ) -> bool:
        """Send success notification."""
        webhook_url = WebhookNotifier.get_webhook_urls().get("registration")
        if not webhook_url:
            return False

        payload = {
            "event": "driver_registered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "driver_id": driver_id,
            "embedding_dimensions": embedding_dimensions,
            "processing_time_ms": processing_time_ms,
            "status": "success",
        }

        return await WebhookNotifier._send_webhook(webhook_url, payload, "registration")

    @staticmethod
    async def notify_device_overuse(
        device_fingerprint: str,
        driver_count: int,
    ) -> bool:
        """Notify of device with too many drivers."""
        webhook_url = WebhookNotifier.get_webhook_urls().get("alert")
        if not webhook_url:
            return False

        payload = {
            "event": "device_overuse_detected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_fingerprint": device_fingerprint,
            "registered_drivers": driver_count,
            "action_required": True,
        }

        return await WebhookNotifier._send_webhook(webhook_url, payload, "device_monitoring")

    @staticmethod
    async def _send_webhook(
        url: str,
        payload: Dict[str, Any],
        event_type: str,
    ) -> bool:
        """
        Generic method to send webhook.

        Args:
            url: Webhook URL
            payload: JSON payload
            event_type: Type of event for logging

        Returns:
            True if successful
        """
        if not url:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(
                            f"✅ Webhook sent | type={event_type} | status={response.status}"
                        )
                        return True
                    else:
                        logger.error(
                            f"❌ Webhook failed | type={event_type} | status={response.status}"
                        )
                        return False
        except asyncio.TimeoutError:
            logger.error(f"❌ Webhook timeout | type={event_type}")
            return False
        except Exception as e:
            logger.error(f"❌ Webhook error | type={event_type} | error={e}")
            return False
