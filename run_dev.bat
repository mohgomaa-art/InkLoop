@echo off
setlocal
title InkLoop Studio - Development Mode (Hot Reload)

echo ======================================================================
echo                  INKLOOP STUDIO - HOT-RELOAD DEV MODE
echo ======================================================================
echo.

:: 1. Verify Python and Node
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your PATH.
    pause
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in your PATH.
    pause
    exit /b 1
)

:: 2. Ensure frontend dependencies installed
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo [INFO] Launching FastAPI Backend on http://127.0.0.1:8000 (auto-reload)...
start "InkLoop API Backend" cmd /k "python scripts\run_server.py --port 8000 --reload"

echo [INFO] Launching Vite Frontend Dev Server on http://127.0.0.1:5173...
start "" http://127.0.0.1:5173/

cd frontend
call npm run dev
