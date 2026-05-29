# Antigravity Fraud Shield — Layer 1
### Driver Registration & Biometric Hashing

> **Stack:** Python · FastAPI · InsightFace (buffalo_l, 512-D ArcFace) · aiosqlite · HTML5/WebRTC

---

## Project Structure

```
antigravity-fraud-plugin/
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── config.py                # Centralised constants (DB path, model name)
│   ├── requirements.txt
│   ├── db/
│   │   └── database.py          # SQLite schema init (aiosqlite)
│   ├── models/
│   │   └── driver_model.py      # Pydantic request / response models
│   ├── routers/
│   │   └── driver.py            # POST /register-driver · GET /drivers
│   └── services/
│       └── face_service.py      # InsightFace embedding pipeline + timing
│
└── frontend/
    ├── index.html               # 4-step registration wizard
    ├── css/style.css            # Dark glassmorphism design system
    └── js/
        ├── api.js               # fetch wrappers + device fingerprint
        ├── liveness.js          # LivenessChecker (pixel-delta engine)
        ├── camera.js            # CameraManager (WebRTC + SVG oval)
        └── app.js               # Step orchestration
```

---

## Quick Start

### 1 — Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 + |
| pip | latest |
| CMake | 3.20+ *(only needed if insightface builds from source)* |
| Visual C++ Build Tools | 2019+ *(Windows, same caveat)* |

> **Tip (Windows):** `insightface` is distributed as a wheel for common Python/OS combos.  
> Run `pip install insightface` first — if it fails with a compile error, install  
> [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) then retry.

---

### 2 — Install Python dependencies

```powershell
cd antigravity-fraud-plugin\backend
pip install -r requirements.txt
```

> **First run note:** InsightFace will download the `buffalo_l` model pack (~330 MB)  
> to `%USERPROFILE%\.insightface\models\buffalo_l\` on the first API call.  
> Subsequent calls use the cached weights.

---

### 3 — Start the backend

```powershell
# From the backend/ directory:
uvicorn main:app --reload --port 8000
```

Or double-click **`start_backend.bat`** in the project root.

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/api/v1/health` | Health probe |

---

### 4 — Open the frontend

Simply open `frontend/index.html` in **Chrome 90+** (or any Chromium browser).  
No build step required — pure HTML5 + Vanilla JS.

> Chrome must be allowed to access your camera.  
> If using VS Code, the **Live Server** extension (`Go Live`) serves the files  
> over `http://localhost:5500` which avoids some `file://` security restrictions.

---

## API Reference

### `POST /api/v1/register-driver`

**Request body (JSON):**

```json
{
  "driver_id":          "DRV-001",
  "device_fingerprint": "a3f9c012",
  "image_base64":       "data:image/jpeg;base64,/9j/4AAQ...",
  "liveness_passed":    true
}
```

**Success response (200):**

```json
{
  "status":                "success",
  "driver_id":             "DRV-001",
  "embedding_dimensions":  512,
  "processing_time_ms":    241.7,
  "registered_at":         "2026-05-29T13:00:00+00:00",
  "message":               "Driver 'DRV-001' registered successfully with a 512-D ArcFace embedding."
}
```

**Error responses:**

| Code | Condition |
|------|-----------|
| 422  | `liveness_passed: false` or no face detected |
| 500  | Unexpected server error |

---

### `GET /api/v1/drivers`

Returns an array of registered driver summaries. **Face vectors are never exposed.**

```json
[
  {
    "driver_id":           "DRV-001",
    "device_fingerprint":  "a3f9c012",
    "registered_at":       "2026-05-29T13:00:00+00:00",
    "embedding_model":     "insightface_buffalo_l_512d",
    "embedding_dimensions": 512
  }
]
```

---

### `GET /api/v1/health`

```json
{
  "status":          "ok",
  "layer":           "Layer 1 – Driver Registration & Biometric Hashing",
  "version":         "1.0.0",
  "embedding_model": "insightface_buffalo_l_512d"
}
```

---

## Data Schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS drivers (
    driver_id          TEXT PRIMARY KEY,
    device_fingerprint TEXT NOT NULL,
    face_vector        TEXT NOT NULL,   -- JSON array of 512 floats
    registered_at      TEXT NOT NULL,   -- ISO-8601 UTC
    embedding_model    TEXT NOT NULL
);
```

Re-registering the same `driver_id` **upserts** (overwrites) the existing record.

---

## Frontend Flow

```
[Setup]  Enter Driver ID → Backend health-check
   │
[Position] Camera opens · SVG oval guide · Face centering indicators
   │
[Liveness] Random challenge (Blink / Smile / Nod / Turn) · 5-second countdown
           · Pixel-delta motion bar · auto-captures on pass
   │
[Result]  POST → 512-D embedding generated → SQLite stored → Success card
```

---

## Liveness Check — How It Works

1. A random action is selected from `["Blink", "Smile", "Turn Head Left", "Turn Head Right", "Nod"]`.
2. Every **80 ms**, an `ImageData` frame is sampled from the oval face region.
3. The average absolute per-channel pixel delta is computed vs. the previous frame.
4. If the **rolling-window maximum** exceeds `MOTION_THRESHOLD = 11`, liveness is confirmed.
5. A 5-second countdown runs in parallel — the check proceeds even if liveness is not confirmed
   (marked as `liveness_passed: false` in the API payload).

> ⚠️ **This is a mock Layer-1 implementation.** Production anti-spoofing requires a dedicated
> ML model (e.g., Silent-Face, DepthAnything, or a commercial liveness SDK).

---

## Notes

- `face_vector` is serialised as `json.dumps(list[float])` in SQLite and never returned via the API.
- The device fingerprint is a client-side FNV-1a hash of navigator/screen properties — it is not
  cryptographically secure but sufficient for device correlation in Layer 1.
- CORS is open (`allow_origins=["*"]`) for local development. Restrict in production.
