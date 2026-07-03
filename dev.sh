#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Ports ──────────────────────────────────────────────
API_PORT=8000
WEB_PORT=5173

# ── Kill existing processes on our ports ───────────────
kill_port() {
    local port=$1 name=$2
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "  Killing $name (port $port) — PID(s): $pids"
        kill "$pids" 2>/dev/null || true
        for i in $(seq 1 10); do
            if ! lsof -ti :"$port" &>/dev/null; then
                break
            fi
            sleep 0.2
        done
    fi
}

echo "==> Clearing ports..."
kill_port $API_PORT "API"
kill_port $WEB_PORT "Web"

# ── Start API (backend) ────────────────────────────────
echo "==> Starting API on port $API_PORT..."
cd "$ROOT_DIR/apps/api"
export PYTHONPATH="$ROOT_DIR/apps/api/src"
nohup "$ROOT_DIR/apps/api/.venv/bin/python" -c "
import uvicorn
uvicorn.run('api.main:app', host='0.0.0.0', port=$API_PORT, reload=True, log_level='info')
" > /tmp/dataproof-api.log 2>&1 &
API_PID=$!
echo "  PID: $API_PID — logs: /tmp/dataproof-api.log"

# ── Start Web (frontend) ───────────────────────────────
echo "==> Starting Web on port $WEB_PORT..."
cd "$ROOT_DIR/apps/web"
nohup npm run dev > /tmp/dataproof-web.log 2>&1 &
WEB_PID=$!
echo "  PID: $WEB_PID — logs: /tmp/dataproof-web.log"

# ── Wait for API to be ready ───────────────────────────
echo "==> Waiting for API..."
for i in $(seq 1 15); do
    if curl -s http://localhost:$API_PORT/health >/dev/null 2>&1; then
        echo "  API ready."
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "  WARNING: API did not respond. Check /tmp/dataproof-api.log"
    fi
    sleep 1
done

# ── Trap to clean up on exit ───────────────────────────
cleanup() {
    echo ""
    echo "==> Shutting down..."
    kill "$API_PID" "$WEB_PID" 2>/dev/null || true
    wait "$API_PID" "$WEB_PID" 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

echo ""
echo "── Services ──────────────────────────────"
echo "  API  → http://localhost:$API_PORT"
echo "  Web  → http://localhost:$WEB_PORT"
echo "  Docs → http://localhost:$API_PORT/docs"
echo "──────────────────────────────────────────"
echo "Press Ctrl+C to stop both."
echo ""

wait
