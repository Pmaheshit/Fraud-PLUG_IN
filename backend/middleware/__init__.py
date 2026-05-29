"""
rate_limiter.py – Rate limiting middleware using slowapi.
Implements:
- Per-IP rate limits
- Per-driver rate limits
- Per-endpoint specific limits
"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

logger = logging.getLogger(__name__)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)


# Rate limit strategies
RATE_LIMITS = {
    "register_driver": "3/day;10/hour;2/minute",  # 3 registrations per day max
    "create_session": "5/minute;50/hour",  # 5 sessions per minute
    "list_drivers": "30/minute;500/hour",  # Open endpoint
    "health_check": "1000/hour",  # Health checks are frequent
    "verify_driver": "10/minute;100/hour",  # Verification attempts
}


def get_rate_limit(endpoint: str) -> str:
    """Get rate limit for an endpoint."""
    return RATE_LIMITS.get(endpoint, "100/hour")


async def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit error handler."""
    logger.warning(
        f"⚠️  Rate limit exceeded | ip={request.client.host} | path={request.url.path}"
    )
    return {
        "detail": "Rate limit exceeded. Please try again later.",
        "retry_after": exc.detail,
    }
