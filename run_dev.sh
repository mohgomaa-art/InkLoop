#!/usr/bin/env bash
# ==============================================================================
# InkLoop Studio - Development Mode (Linux / macOS)
# ==============================================================================
set -e

cd "$(dirname "$0")"

echo "======================================================================"
echo "                 INKLOOP STUDIO - HOT-RELOAD DEV MODE"
echo "======================================================================"
echo ""

if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in your PATH."
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] npm is not installed or not in your PATH."
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

HOST="${HOST:-127.0.0.1}"
BACKEND_PORT="${PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "[INFO] Launching FastAPI Backend on http://${HOST}:${BACKEND_PORT} (auto-reload)..."
$PY_CMD scripts/run_server.py --host "$HOST" --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

trap "kill $BACKEND_PID 2>/dev/null || true" EXIT

echo "[INFO] Launching Vite Frontend Dev Server on http://${HOST}:${FRONTEND_PORT}..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://${HOST}:${FRONTEND_PORT}/" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "http://${HOST}:${FRONTEND_PORT}/" >/dev/null 2>&1 &
fi

cd frontend
npm run dev
