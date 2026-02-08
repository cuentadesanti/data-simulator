#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_CMD=(uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload)
FRONTEND_CMD=(npm run dev -- --host 0.0.0.0 --port 5173)

kill_workspace_listener_on_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return
  fi

  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    local cmd
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"

    if [[ "$cmd" == *"$ROOT_DIR"* ]]; then
      echo "[dev] freeing port $port by stopping workspace process pid=$pid"
      kill "$pid" 2>/dev/null || true
    else
      echo "[dev] port $port is already in use by a non-workspace process:"
      echo "      pid=$pid cmd=$cmd"
      echo "[dev] stop that process manually or change the port."
      exit 1
    fi
  done <<< "$pids"
}

# Reclaim common dev ports if they are occupied by this workspace.
kill_workspace_listener_on_port 8000
kill_workspace_listener_on_port 5173

echo "[dev] starting backend: ${BACKEND_CMD[*]}"
(
  cd "$BACKEND_DIR"
  "${BACKEND_CMD[@]}"
) &
BACKEND_PID=$!

echo "[dev] starting frontend: ${FRONTEND_CMD[*]}"
(
  cd "$FRONTEND_DIR"
  "${FRONTEND_CMD[@]}"
) &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "[dev] stopping services..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "[dev] frontend: http://localhost:5173"
echo "[dev] backend:  http://localhost:8000"
echo "[dev] press Ctrl+C to stop"

wait -n "$BACKEND_PID" "$FRONTEND_PID"
