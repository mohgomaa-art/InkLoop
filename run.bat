@echo off
setlocal
title InkLoop Studio - Manga and Comic Production System

echo ======================================================================
echo                      INKLOOP PRODUCTION STUDIO
echo          Research-Driven Manga, Manhwa and Comics Production
echo ======================================================================
echo.

:: 1. Verify Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.11+ and ensure it is added to your PATH.
    echo.
    pause
    exit /b 1
)

:: 2. Verify or Build Frontend Dist
if not exist "frontend\dist\index.html" (
    echo [INFO] Frontend distribution bundle not detected.
    echo [INFO] Building production bundle...
    echo.
    
    cd frontend
    if not exist "node_modules" (
        echo [INFO] Installing frontend npm dependencies...
        call npm install
        if errorlevel 1 (
            echo [ERROR] npm install failed.
            cd ..
            pause
            exit /b 1
        )
    )
    
    echo [INFO] Running production build...
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Frontend build failed.
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [INFO] Frontend build completed successfully.
    echo.
)

:: 3. Launch Default Browser
echo [INFO] Starting InkLoop Unified Production Server...
echo [INFO] Studio Interface: http://127.0.0.1:8000/
echo [INFO] Swagger API Docs: http://127.0.0.1:8000/api/docs
echo.

:: Open browser
start "" http://127.0.0.1:8000/

:: 4. Run Server
python scripts\run_server.py --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo.
    echo [ERROR] Server terminated unexpectedly.
    pause
)
