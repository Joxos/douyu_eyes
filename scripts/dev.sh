#!/usr/bin/env bash
set -euo pipefail

# Dev startup script: run backend (uvicorn) and frontend (pnpm) reliably
# - Resolves project root so it can be run from any cwd
# - Ensures .venv exists (creates with 'uv venv' if missing)
# - Installs backend deps via 'uv pip install -r requirements.txt'
# - Sets PYTHONPATH to project root
# - Loads DYKIT_DSN from env if present; warns if absent
# - Starts backend and frontend, traps SIGINT/SIGTERM to kill children

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Project root: $ROOT_DIR"

# Ensure uv is available (uv - is Uprading tool wrapper). We won't fail if missing; just warn.
if ! command -v uv >/dev/null 2>&1; then
  echo "Warning: 'uv' command not found. .venv may not be created or dependencies installed via 'uv'."
fi

# Ensure .venv exists
if [ ! -d "$ROOT_DIR/.venv" ]; then
  echo ".venv not found. Creating via: uv venv"
  if command -v uv >/dev/null 2>&1; then
    uv venv
  else
    echo "Error: 'uv' not found; cannot create .venv automatically." >&2
    echo "Please create a virtualenv at $ROOT_DIR/.venv (python -m venv .venv) and re-run this script." >&2
    exit 1
  fi
fi

echo "Activating .venv"
# shellcheck disable=SC1090
source "$ROOT_DIR/.venv/bin/activate"

# Install backend dependencies (idempotent)
if [ -f "$ROOT_DIR/requirements.txt" ]; then
  echo "Installing backend dependencies from requirements.txt"
  uv pip install -r requirements.txt || pip install -r requirements.txt
else
  echo "No requirements.txt found in project root; skipping backend dependency installation"
fi

# Export PYTHONPATH to include project root
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
echo "PYTHONPATH set to: $PYTHONPATH"

# DYKIT_DSN handling
if [ -z "${DYKIT_DSN:-}" ]; then
  echo "Warning: DYKIT_DSN not set. Continuing without DYKIT_DSN." >&2
else
  echo "DYKIT_DSN is set."
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

echo "Starting backend on 0.0.0.0:$BACKEND_PORT"
echo "Starting frontend on 0.0.0.0:$FRONTEND_PORT"

PIDS=()

start_backend() {
  # Start uvicorn in background
  uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
  PIDS+=("$!")
  echo "Backend PID: ${PIDS[-1]}"
}

start_frontend() {
  if [ -d "$ROOT_DIR/frontend" ] && [ -f "$ROOT_DIR/frontend/package.json" ]; then
    (cd "$ROOT_DIR/frontend" && pnpm dev --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort) &
    PIDS+=("$!")
    echo "Frontend PID: ${PIDS[-1]}"
  else
    echo "Frontend directory or package.json not found; skipping frontend start" >&2
  fi
}

shutdown() {
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "Killing PID $pid"
      kill "$pid" || true
    fi
  done
  wait || true
  echo "Exited"
  exit 0
}

trap shutdown INT TERM

start_backend
start_frontend

echo "Access the app at:"
echo "  Backend: http://0.0.0.0:$BACKEND_PORT/docs"
echo "  Frontend: http://0.0.0.0:$FRONTEND_PORT"

# Wait on background processes
wait
