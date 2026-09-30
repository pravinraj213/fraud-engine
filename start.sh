#!/usr/bin/env bash
# Start the fraud-rule-engine backend (port 8000) and reviewer console (port 5173) together.
#
#   ./start.sh              start both; alerts are only written to the server log
#   ./start.sh --email      send HIGH-risk alerts as real email through Amazon SES
#   ./start.sh --reset      delete backend/fraud.db first (clean demo)
#   ./start.sh --simulate   also run the command-line simulator once the API is up
#
# Anything already listening on ports 8000/5173 is stopped first. Ctrl+C stops both servers.
# First run creates backend/.venv and installs frontend packages automatically.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"
RESET=false
SIMULATE=false
EMAIL=false

for arg in "$@"; do
  case "$arg" in
    --reset) RESET=true ;;
    --simulate) SIMULATE=true ;;
    --email) EMAIL=true ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg (see --help)" >&2; exit 1 ;;
  esac
done

log() { printf '\033[1;34m[start]\033[0m %s\n' "$*"; }

# Email is opt-in: this overrides NOTIFIER in backend/.env for this run.
if $EMAIL; then
  export NOTIFIER=ses
  log "Email alerts ON: HIGH-risk transactions send real email through SES (capped per day by ALERT_DAILY_LIMIT)."
else
  export NOTIFIER=log
  log "Email alerts OFF: alerts are written to the server log. Use --email to send real email."
fi

# Alert emails link to the console. Use this machine's network address so the link also opens on
# other devices on the same network (a localhost link only works on this computer).
if [ -z "${CONSOLE_BASE_URL:-}" ]; then
  LAN_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p' | head -1)
  export CONSOLE_BASE_URL="http://${LAN_IP:-localhost}:$UI_PORT"
fi
log "Console links in alerts: $CONSOLE_BASE_URL"

port_pids() { lsof -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true; }

# Free the ports: stop whatever is already listening (e.g. a previous run of this script).
free_port() {
  local port=$1 pids
  pids=$(port_pids "$port")
  [ -z "$pids" ] && return 0
  for pid in $pids; do
    log "Port $port is in use by PID $pid ($(ps -o comm= -p "$pid" 2>/dev/null || echo '?')); stopping it."
  done
  kill $pids 2>/dev/null || true
  for _ in $(seq 20); do
    [ -z "$(port_pids "$port")" ] && return 0
    sleep 0.25
  done
  pids=$(port_pids "$port")
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  sleep 0.5
  if [ -n "$(port_pids "$port")" ]; then
    echo "Could not free port $port." >&2
    exit 1
  fi
}
free_port "$API_PORT"
free_port "$UI_PORT"

# --- dependencies ---------------------------------------------------------------------------
if [ ! -x "$BACKEND/.venv/bin/uvicorn" ]; then
  log "Creating backend virtual environment and installing requirements…"
  python3 -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"
fi
if [ ! -d "$FRONTEND/node_modules" ]; then
  log "Installing frontend packages…"
  (cd "$FRONTEND" && npm install --silent)
fi
if [ ! -f "$BACKEND/.env" ]; then
  log "No backend/.env found; copying .env.example (alerts go to the server log)."
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi
if $RESET; then
  log "Deleting backend/fraud.db for a clean start."
  rm -f "$BACKEND/fraud.db"
fi

# --- run --------------------------------------------------------------------------------------
PIDS=()
cleanup() {
  trap - INT TERM EXIT
  log "Stopping…"
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

log "Starting API on http://localhost:$API_PORT (docs at /docs)"
(cd "$BACKEND" && exec .venv/bin/uvicorn app.main:app --reload --port "$API_PORT") &
PIDS+=($!)

log "Starting console on http://localhost:$UI_PORT"
(cd "$FRONTEND" && API_TARGET="http://localhost:$API_PORT" exec npx vite --port "$UI_PORT" --strictPort) &
PIDS+=($!)

for _ in $(seq 60); do
  curl -sf "http://localhost:$API_PORT/api/health" >/dev/null && break
  sleep 0.5
done
curl -sf "http://localhost:$API_PORT/api/health" >/dev/null || { echo "API did not start; see the log above." >&2; exit 1; }
log "API is healthy."

if $SIMULATE && $EMAIL; then
  read -r -p "The simulator creates about 4 HIGH-risk transactions, each sending a real email. Run it? [y/N] " answer || answer=""
  [[ "$answer" =~ ^[Yy]$ ]] || { SIMULATE=false; log "Skipping the simulator."; }
fi
if $SIMULATE; then
  log "Running the simulator…"
  "$BACKEND/.venv/bin/python" "$ROOT/simulator/generate_transactions.py" --base-url "http://localhost:$API_PORT" || true
fi

log "Ready: open http://localhost:$UI_PORT  (simulator at /simulator; Ctrl+C to stop)"
wait
