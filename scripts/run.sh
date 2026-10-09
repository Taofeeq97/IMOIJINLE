#!/usr/bin/env bash
# Start backend + frontend for local development.
# Usage (from repo root):
#   ./scripts/run.sh
#   ./scripts/run.sh --seed
#   BACKEND_PORT=8000 ./scripts/run.sh
#
# Requires: uv, pnpm, Node 22+
# Ctrl+C stops both processes.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
USE_SQLITE="${USE_SQLITE:-true}"
CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-true}"
SEED=0

for arg in "$@"; do
  case "$arg" in
    --seed) SEED=1 ;;
    -h|--help)
      echo "Usage: $0 [--seed]"
      echo "  --seed   Run manage.py seed_demo before starting"
      echo "Env: BACKEND_PORT (default 8080), FRONTEND_PORT (default 3000), USE_SQLITE (default true)"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing dependency: $1" >&2
    exit 1
  }
}

need uv
need pnpm

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Stopping…"
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

export USE_SQLITE CELERY_TASK_ALWAYS_EAGER

echo "→ Migrating backend…"
(
  cd "$BACKEND_DIR"
  uv run python manage.py migrate --noinput
)

if [[ "$SEED" -eq 1 ]]; then
  echo "→ Seeding demo data…"
  (
    cd "$BACKEND_DIR"
    uv run python manage.py seed_demo
  )
fi

if [[ ! -f "$FRONTEND_DIR/.env.local" ]]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}" > "$FRONTEND_DIR/.env.local"
  echo "Wrote frontend/.env.local → http://localhost:${BACKEND_PORT}"
fi

echo "→ Backend  http://localhost:${BACKEND_PORT}"
(
  cd "$BACKEND_DIR"
  uv run python manage.py runserver "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "→ Frontend http://localhost:${FRONTEND_PORT}"
(
  cd "$FRONTEND_DIR"
  # Next.js reads PORT; avoid `pnpm dev -- --port` (Next treats `--` as a directory)
  PORT="$FRONTEND_PORT" pnpm dev
) &
FRONTEND_PID=$!

echo ""
echo "Running. Demo password: DemoPass123!"
echo "  student@imoijinle.local  |  superadmin@imoijinle.local"
echo "Ctrl+C to stop."
echo ""

wait
