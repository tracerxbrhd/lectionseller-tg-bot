#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  printf 'ERROR: Docker Compose is not available.\n' >&2
  exit 1
fi

"${COMPOSE[@]}" run --rm web python -m app.cli.seed_demo_catalog "$@"
