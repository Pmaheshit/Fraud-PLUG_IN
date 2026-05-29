"""
database.py – SQLite connection management and schema initialisation.

Uses aiosqlite for async-compatible reads/writes that integrate cleanly
with FastAPI's async event loop.
"""
import aiosqlite
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Create the `drivers` table if it does not already exist.
    Called once during application startup via the FastAPI lifespan hook.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                driver_id          TEXT PRIMARY KEY,
                device_fingerprint TEXT NOT NULL,
                face_vector        TEXT NOT NULL,   -- JSON-serialised list[float]
                registered_at      TEXT NOT NULL,   -- ISO-8601 UTC timestamp
                embedding_model    TEXT NOT NULL
            )
            """
        )
        await db.commit()

    logger.info("✅ Database ready at: %s", DB_PATH)
