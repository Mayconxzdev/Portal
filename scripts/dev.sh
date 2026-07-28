#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
WEB_DIR="$ROOT_DIR/apps/web"

cleanup() {
  local exit_code=$?
  trap - INT TERM EXIT
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  exit "$exit_code"
}
trap cleanup INT TERM EXIT

cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[portal] .env criado a partir de .env.example. Revise os valores local-dev-* antes de continuar."
fi

echo "[portal] Iniciando PostgreSQL, Redis, MinIO, n8n e serviços auxiliares..."
docker compose -f infra/docker-compose.yml up -d

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements-dev.txt"

(
  cd "$BACKEND_DIR"
  alembic upgrade head
)
python "$ROOT_DIR/scripts/seed_dev.py"

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  npm --prefix "$WEB_DIR" ci
fi

(
  cd "$BACKEND_DIR"
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
BACKEND_PID=$!

npm --prefix "$WEB_DIR" run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "Portal:  http://localhost:5173"
echo "API:     http://localhost:8000/docs"
echo "Login local após o seed: ${PORTAL_DEV_ADMIN_USER:-vesper_admin} / ${PORTAL_DEV_ADMIN_PASSWORD:-portal-dev-only}"
echo "Pressione Ctrl+C para encerrar os servidores locais."

wait -n "$BACKEND_PID" "$FRONTEND_PID"
