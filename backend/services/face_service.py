"""
face_service.py – InsightFace 512-D ArcFace embedding generation.

The FaceAnalysis model is loaded once at module level (lazy singleton) so
subsequent calls share the same warm model without reloading weights.

Pipeline:
  1. Strip data-URI prefix from the incoming base64 string
  2. Decode bytes → PIL Image → RGB NumPy array → BGR (OpenCV convention)
  3. Run InsightFace detection + recognition
  4. Return the 512-D float list and wall-clock processing time in ms
"""
from __future__ import annotations

import base64
import io
import logging
import time
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ── Lazy singleton ────────────────────────────────────────────────────────────
_face_app = None


def _get_face_app():
    """
    Initialise InsightFace FaceAnalysis once and cache it globally.
    The buffalo_l pack is downloaded automatically to ~/.insightface/models/
    on the first call (~330 MB).
    """
    global _face_app
    if _face_app is None:
        # Import here so the module-level import cost is deferred
        from insightface.app import FaceAnalysis  # type: ignore

        logger.info(
            "⏳ Loading InsightFace model 'buffalo_l' "
            "(first run downloads ~330 MB) …"
        )
        _face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("✅ InsightFace model ready.")
    return _face_app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode_image(image_base64: str) -> np.ndarray:
    """
    Convert a base64 string (with or without a data-URI prefix) into a
    BGR NumPy array suitable for InsightFace.
    """
    # Strip optional data-URI prefix  e.g. "data:image/jpeg;base64,..."
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    raw_bytes = base64.b64decode(image_base64)
    pil_image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    rgb_array = np.array(pil_image, dtype=np.uint8)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_array


# ── Public API ────────────────────────────────────────────────────────────────

def generate_embedding(image_base64: str) -> Tuple[List[float], float]:
    """
    Generate a 512-dimensional ArcFace embedding from a base64 image.

    Args:
        image_base64: Base64-encoded JPEG (data-URI prefix is optional).

    Returns:
        A tuple of:
          - embedding  : list[float] of length 512
          - elapsed_ms : wall-clock processing time in milliseconds

    Raises:
        ValueError: If no face is detected in the provided image.
        RuntimeError: If the InsightFace model fails unexpectedly.
    """
    face_app = _get_face_app()

    t_start = time.perf_counter()

    try:
        bgr_image = _decode_image(image_base64)
    except Exception as exc:
        raise ValueError(f"Image decoding failed: {exc}") from exc

    faces = face_app.get(bgr_image)

    elapsed_ms = (time.perf_counter() - t_start) * 1_000

    if not faces:
        raise ValueError(
            "No face detected in the provided image. "
            "Ensure the subject is well-lit and faces the camera directly."
        )

    if len(faces) > 1:
        logger.warning(
            "Multiple faces detected (%d). Selecting the largest bounding box.",
            len(faces),
        )
        faces = sorted(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )

    embedding: np.ndarray = faces[0].embedding  # shape: (512,)
    vector: List[float] = embedding.tolist()

    logger.info(
        "🧠 Embedding generated | dim=%d | det_score=%.3f | time=%.2f ms",
        len(vector),
        float(faces[0].det_score),
        elapsed_ms,
    )

    return vector, elapsed_ms
