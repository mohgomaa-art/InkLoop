#!/usr/bin/env bash
# ==============================================================================
# InkLoop Production Studio Launcher (Linux / macOS)
# ==============================================================================
set -e

# Change to script directory
cd "$(dirname "$0")"

echo "======================================================================"
echo "                     INKLOOP PRODUCTION STUDIO"
echo "         Research-Driven Manga, Manhwa and Comics Production"
echo "======================================================================"
echo ""

# 1. Verify Python
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in your PATH."
    echo "Please install Python 3.11+."
    exit 1
fi

# 2. Build Frontend Dist if missing
if [ ! -f "frontend/dist/index.html" ]; then
    echo "[INFO] Frontend distribution bundle not detected."
    echo "[INFO] Building production bundle..."
    echo ""

    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "[INFO] Installing frontend npm dependencies..."
        npm install
    fi

    echo "[INFO] Running production build..."
    npm run build
    cd ..
    echo "[INFO] Frontend build completed successfully."
    echo ""
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "[INFO] Starting InkLoop Unified Production Server..."
echo "[INFO] Studio Interface: http://${HOST}:${PORT}/"
echo "[INFO] Swagger API Docs: http://${HOST}:${PORT}/api/docs"
echo ""

# Launch browser if command exists
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://${HOST}:${PORT}/" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "http://${HOST}:${PORT}/" >/dev/null 2>&1 &
fi

exec $PY_CMD scripts/run_server.py --host "$HOST" --port "$PORT"
