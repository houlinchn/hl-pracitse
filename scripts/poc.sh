#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
compose() { docker compose -p hl-pracitse-poc "$@"; }
case "${1:-help}" in
  up)
    python3 scripts/configure.py
    compose build
    compose up -d --wait db
    compose run --rm --no-deps api uv run --frozen --no-dev python -m poc.cli init-db
    compose up -d --wait api web
    python3 - <<'PY'
import time
import urllib.request
for attempt in range(30):
    try:
        with urllib.request.urlopen('http://127.0.0.1:13080/api/health', timeout=2) as response:
            if response.status == 200:
                break
    except (OSError, ValueError):
        time.sleep(1)
else:
    raise SystemExit('POC readiness failed; inspect: docker compose -p hl-pracitse-poc logs api web')
print('POC ready: http://127.0.0.1:13080 (web), http://127.0.0.1:13081/docs (OpenAPI)')
PY
    ;;
  staff)
    compose run --rm --no-deps --user "$(id -u):$(id -g)" \
      --volume "$PWD/.local/staff-password:/run/poc-staff-password:ro" \
      api /app/.venv/bin/python -m poc.cli create-staff \
      --email staff@example.com --password-file /run/poc-staff-password \
      --permission applications.read --permission applications.advance --permission audit.read
    ;;
  stop) compose stop ;;
  down) compose down ;;
  status) compose ps ;;
  *) printf '%s\n' 'Usage: scripts/poc.sh {up|staff|status|stop|down}' 'up: configure, build, initialize isolated schema, start; staff: explicitly create demo staff' 'stop/down preserve the dedicated PostgreSQL volume. See runbook for deliberate data deletion.' ;;
esac
