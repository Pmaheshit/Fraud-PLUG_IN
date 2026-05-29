"""
main.py – FastAPI application entrypoint with security features.

Start the server from the `backend/` directory:
    uvicorn main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc

Security Features:
- Rate limiting (slowapi)
- Audit logging
- JWT authentication
- Request signing
- Fraud detection
- Webhook alerts
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config import API_PREFIX, APP_DESCRIPTION, APP_TITLE, APP_VERSION
from db.database import init_db
from routers import auth, driver
from security import AuditLogger
from middleware import limiter, rate_limit_error_handler

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Antigravity Fraud Shield – Layer 1 starting …")
    logger.info("🔒 Initializing security features…")
    
    # Initialize database
    await init_db()
    
    # Initialize audit logging
    await AuditLogger.init_audit_table()
    
    logger.info("✅ Security features enabled: Rate Limiting, Audit Log, JWT, Fraud Detection, Webhooks")
    logger.info("📡 API ready at http://localhost:8000%s", API_PREFIX)
    yield
    logger.info("🛑 Server shutting down.")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

# CORS – open for local development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(driver.router, prefix=API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(f"{API_PREFIX}/health", tags=["System"])
async def health_check(request=None) -> dict:
    """
    Lightweight liveness probe.
    Returns 200 OK with basic metadata so the frontend can confirm
    the backend is reachable before starting the camera flow.
    """
    return {
        "status": "ok",
        "layer": "Layer 1 – Driver Registration & Biometric Hashing",
        "version": APP_VERSION,
        "embedding_model": "insightface_buffalo_l_512d",
        "security_features": [
            "Rate Limiting",
            "Audit Logging",
            "Fraud Detection",
            "JWT Authentication",
            "Request Signing",
            "Webhook Alerts",
        ],
    }
