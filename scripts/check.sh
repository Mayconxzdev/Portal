#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT_DIR/scripts/validate_public_release.py"

(
  cd "$ROOT_DIR/backend"
  ruff check app tests
  python -m compileall -q app alembic
  ENVIRONMENT=testing PYTHONPATH=. pytest -q
)

npm --prefix "$ROOT_DIR/apps/web" run lint
npm --prefix "$ROOT_DIR/apps/web" run test:run
npm --prefix "$ROOT_DIR/apps/web" run build
