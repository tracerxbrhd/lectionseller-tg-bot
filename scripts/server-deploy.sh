#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log() {
  printf '\n==> %s\n' "$1"
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "Docker Compose is not available. Run scripts/server-install-ubuntu.sh first."
fi

compose() {
  "${COMPOSE[@]}" "$@"
}

env_value() {
  local key="$1"
  if [[ ! -f .env ]]; then
    return 0
  fi
  grep -E "^${key}=" .env | tail -n 1 | cut -d '=' -f 2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

require_env() {
  local key="$1"
  local value
  value="$(env_value "$key")"
  if [[ -z "$value" ]]; then
    fail "Set $key in .env before deployment."
  fi
  printf '%s' "$value"
}

validate_env() {
  [[ -f .env ]] || {
    cp .env.example .env
    fail ".env was created from .env.example. Fill production secrets and run this script again."
  }

  local bot_token app_secret db_password app_env app_debug base_url allowed_hosts web_bind_host
  bot_token="$(require_env BOT_TOKEN)"
  app_secret="$(require_env APP_SECRET_KEY)"
  db_password="$(require_env DATABASE_PASSWORD)"
  app_env="$(env_value APP_ENV)"
  app_debug="$(env_value APP_DEBUG)"
  base_url="$(env_value BASE_URL)"
  allowed_hosts="$(env_value ALLOWED_HOSTS)"
  web_bind_host="$(env_value WEB_BIND_HOST)"

  [[ "$bot_token" != "replace-with-telegram-bot-token" ]] || fail "Replace BOT_TOKEN in .env."
  [[ "$app_secret" != change-me* ]] || fail "Replace APP_SECRET_KEY with a long random secret."
  [[ "$db_password" != "change-me-db-password" && "$db_password" != "lectionseller" ]] \
    || fail "Replace DATABASE_PASSWORD with a strong password."

  if [[ "${app_env:-}" != "production" ]]; then
    printf 'WARNING: APP_ENV is "%s", expected "production" for VPS.\n' "${app_env:-empty}" >&2
  fi

  if [[ "${app_debug:-}" != "false" ]]; then
    printf 'WARNING: APP_DEBUG is "%s", expected "false" for VPS.\n' "${app_debug:-empty}" >&2
  fi

  if [[ -z "$base_url" || "$base_url" == http://localhost* ]]; then
    printf 'WARNING: BASE_URL is "%s". Set public HTTPS URL for YooKassa webhooks.\n' "${base_url:-empty}" >&2
  fi

  if [[ "$base_url" != https://* ]]; then
    printf 'WARNING: BASE_URL is "%s". HTTPS is expected for production.\n' "${base_url:-empty}" >&2
  fi

  if [[ -z "$allowed_hosts" || "$allowed_hosts" == "localhost,127.0.0.1" ]]; then
    printf 'WARNING: ALLOWED_HOSTS is "%s". Add public domains for production.\n' "${allowed_hosts:-empty}" >&2
  fi

  if [[ -n "$web_bind_host" && "$web_bind_host" != "127.0.0.1" ]]; then
    printf 'WARNING: WEB_BIND_HOST is "%s". Use 127.0.0.1 behind Nginx in production.\n' "$web_bind_host" >&2
  fi

  if [[ -z "$(env_value YOOKASSA_SHOP_ID)" || -z "$(env_value YOOKASSA_SECRET_KEY)" ]]; then
    printf 'WARNING: YooKassa settings are empty. Bot will create purchases without payment links.\n' >&2
  fi
}

log "Validating .env"
validate_env

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  log "Building web and bot images"
  compose build web bot
fi

log "Starting PostgreSQL and Redis"
compose up -d postgres redis

if [[ "${SKIP_MIGRATIONS:-0}" != "1" ]]; then
  log "Applying Alembic migrations"
  compose run --rm web alembic upgrade head
fi

if [[ "${CREATE_ADMIN:-0}" == "1" ]]; then
  admin_username="${ADMIN_USERNAME:-admin}"
  log "Creating or updating web admin '$admin_username'"
  compose run --rm web python -m app.cli.create_admin --username "$admin_username"
else
  printf '\nSkip admin creation. To create one now, run:\n'
  printf '  CREATE_ADMIN=1 ADMIN_USERNAME=admin ./scripts/server-deploy.sh\n'
fi

if [[ "${SEED_DEMO_CATALOG:-0}" == "1" ]]; then
  log "Seeding demo catalog"
  compose run --rm web python -m app.cli.seed_demo_catalog
fi

log "Starting application services"
compose up -d web bot

log "Service status"
compose ps

web_port="$(env_value WEB_PORT)"
web_port="${web_port:-8000}"

log "Healthcheck"
if command -v curl >/dev/null 2>&1; then
  curl -fsS "http://127.0.0.1:${web_port}/health" >/dev/null
  printf 'Healthcheck OK: http://127.0.0.1:%s/health\n' "$web_port"
else
  printf 'curl is not installed; skip healthcheck.\n'
fi

base_url="$(env_value BASE_URL)"
base_url="${base_url:-http://localhost:${web_port}}"

cat <<EOF

Deployment completed.

Admin panel:
  ${base_url}/admin/login

YooKassa webhook:
  ${base_url}/payments/webhooks/yookassa

Logs:
  ${COMPOSE[*]} logs --tail=100 web
  ${COMPOSE[*]} logs --tail=100 bot
EOF
