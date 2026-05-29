"""
Central configuration constants for the Antigravity Fraud Detection backend.
"""
import os

# ── Database ────────────────────────────────────────────────────────────────
# SQLite file lives in the backend/ directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fraud_detection.db")

# ── InsightFace ──────────────────────────────────────────────────────────────
INSIGHTFACE_MODEL_NAME = "buffalo_l"          # 512-D ArcFace embeddings
INSIGHTFACE_DET_SIZE   = (640, 640)           # detection input resolution
EMBEDDING_MODEL_LABEL  = "insightface_buffalo_l_512d"

# ── API ──────────────────────────────────────────────────────────────────────
API_PREFIX  = "/api/v1"
APP_TITLE   = "Antigravity Fraud Shield API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Layer 1 – Driver Registration & Biometric Hashing. "
    "Captures a facial image, generates a 512-D ArcFace embedding "
    "via InsightFace, and persists it to a SQLite mock store."
)
