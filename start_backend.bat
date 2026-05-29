@echo off
title Antigravity Fraud Shield — Backend (Layer 1)
echo.
echo  ======================================================
echo   ANTIGRAVITY FRAUD SHIELD  ^|  Layer 1 Backend
echo   InsightFace + FastAPI + SQLite
echo  ======================================================
echo.

REM ── Move into the backend directory ─────────────────────────────────────────
cd /d "%~dp0backend"

REM ── Check Python is available ────────────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

REM ── Check uvicorn is installed ────────────────────────────────────────────────
python -m uvicorn --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [INFO] uvicorn not found — installing requirements...
    pip install -r requirements.txt
    echo.
)

echo  [INFO] Starting FastAPI server on http://localhost:8000
echo  [INFO] Swagger UI  → http://localhost:8000/docs
echo  [INFO] Health      → http://localhost:8000/api/v1/health
echo  [INFO] Press Ctrl+C to stop.
echo.

python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0

pause
