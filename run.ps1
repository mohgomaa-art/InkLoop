# ==============================================================================
# InkLoop Production Studio Launcher (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "                     INKLOOP PRODUCTION STUDIO" -ForegroundColor Cyan
Write-Host "         Research-Driven Manga, Manhwa and Comics Production" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "[INFO] Detected Python: $pyVersion"
} catch {
    Write-Error "[ERROR] Python is not installed or not in your PATH. Please install Python 3.11+."
    exit 1
}

# 2. Build Frontend Dist if missing
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "[INFO] Frontend distribution bundle not detected. Building..." -ForegroundColor Yellow
    Push-Location frontend
    if (-not (Test-Path "node_modules")) {
        Write-Host "[INFO] Installing npm dependencies..."
        npm install
    }
    npm run build
    Pop-Location
    Write-Host "[INFO] Frontend build completed." -ForegroundColor Green
}

$hostAddr = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$portNum = if ($env:PORT) { $env:PORT } else { "8000" }

Write-Host "[INFO] Starting InkLoop Unified Production Server..." -ForegroundColor Green
Write-Host "[INFO] Studio Interface: http://${hostAddr}:${portNum}/" -ForegroundColor Green
Write-Host "[INFO] Swagger API Docs: http://${hostAddr}:${portNum}/api/docs" -ForegroundColor Green
Write-Host ""

Start-Process "http://${hostAddr}:${portNum}/"

python scripts\run_server.py --host $hostAddr --port $portNum
