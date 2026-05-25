# Setup And Deployment

English | [Русский](SETUP.ru.md)

This document contains operational instructions for local startup, server deployment, and maintenance of LectionSeller TG Bot.

## ENV

Secrets are stored only in `.env`. The `.env` file is excluded from git.

Create `.env`:

```bash
cp .env.example .env
```

Main variables:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Environment: `local`, `production`, or another value. |
| `APP_DEBUG` | FastAPI debug mode. |
| `APP_LOG_LEVEL` | Logging level. |
| `APP_SECRET_KEY` | Secret for signed admin session cookies. |
| `BASE_URL` | Public web service URL. |
| `ALLOWED_HOSTS` | Allowed HTTP Host headers for the web service. |
| `BOT_TOKEN` | Telegram bot token. |
| `ADMIN_TELEGRAM_IDS` | Comma-separated Telegram admin IDs. |
| `DATABASE_*` | PostgreSQL settings. |
| `REDIS_*` | Redis settings. |
| `WEB_BIND_HOST` | Host/IP where the web service port is published on the server. For production with Nginx: `127.0.0.1`. |
| `WEB_PORT` | Host port for web/admin service. |
| `YOOKASSA_SHOP_ID` | YooKassa shop ID. |
| `YOOKASSA_SECRET_KEY` | YooKassa secret key. |
| `YOOKASSA_RETURN_URL` | Payment return URL. |
| `YOOKASSA_WEBHOOK_ALLOWED_IPS` | YooKassa webhook IP/CIDR allowlist. |
| `UPLOAD_DIR` | Upload directory inside containers. |

Generate `APP_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Local Startup

Quick Windows startup:

```powershell
.\scripts\local-start.ps1
```

Useful flags:

```powershell
.\scripts\local-start.ps1 -CreateAdmin
.\scripts\local-start.ps1 -SeedDemoCatalog
.\scripts\local-start.ps1 -Rebuild
.\scripts\local-start.ps1 -SkipBuild
.\scripts\local-start.ps1 -SkipMigrations
```

Manual startup:

```bash
docker-compose build
docker-compose up -d postgres redis
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web python -m app.cli.create_admin --username admin
docker-compose up -d web bot
```

Checks:

```bash
docker-compose ps
docker-compose logs --tail=80 web
docker-compose logs --tail=80 bot
curl -f http://127.0.0.1:8000/health
```

Admin panel:

```text
http://localhost:8000/admin/login
```

## Demo Catalog

Seed demo sections, blocks, and lectures:

```bash
./scripts/seed-demo-catalog.sh
```

Dry-run without database writes:

```bash
./scripts/seed-demo-catalog.sh --dry-run
```

On Windows:

```powershell
.\scripts\seed-demo-catalog.ps1
```

The command is idempotent: repeated runs update existing records by title instead of creating duplicates. It does not attach lecture materials.

## Ubuntu 24.04 VPS

Install system dependencies:

```bash
chmod +x scripts/server-install-ubuntu.sh scripts/server-deploy.sh
./scripts/server-install-ubuntu.sh
```

If the script added your user to the `docker` group, log out and log in again via SSH.

Prepare `.env`:

```bash
cp .env.example .env
nano .env
```

Production minimum:

```text
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<long-random-secret>
BASE_URL=https://tracerxbrhd.ru
ALLOWED_HOSTS=tracerxbrhd.ru,www.tracerxbrhd.ru,api.tracerxbrhd.ru,localhost,127.0.0.1
BOT_TOKEN=<telegram-bot-token>
DATABASE_PASSWORD=<strong-db-password>
WEB_BIND_HOST=127.0.0.1
YOOKASSA_SHOP_ID=<shop-id>
YOOKASSA_SECRET_KEY=<secret-key>
YOOKASSA_RETURN_URL=https://tracerxbrhd.ru/payments/return
```

Detailed guide for the `tracerxbrhd.ru` domain: [DEPLOY.tracerxbrhd.ru.md](DEPLOY.tracerxbrhd.ru.md).

Deploy:

```bash
./scripts/server-deploy.sh
```

Create an admin during deployment:

```bash
CREATE_ADMIN=1 ADMIN_USERNAME=admin ./scripts/server-deploy.sh
```

Seed demo catalog during deployment:

```bash
SEED_DEMO_CATALOG=1 ./scripts/server-deploy.sh
```

## YooKassa

Webhook endpoint:

```text
http://<SERVER_IP>:8000/payments/webhooks/yookassa
```

For stable production usage, an HTTPS domain is recommended. Without a domain and HTTPS, use the "Check payment" button in Telegram: the bot will request payment status from YooKassa and grant access after successful payment.

## Server Update

```bash
cd ~/lectionseller-tg-bot
git pull
./scripts/server-deploy.sh
```

If local changes exist:

```bash
git status --short
git stash push -m "server local changes"
git pull
./scripts/server-deploy.sh
```

## Backup

PostgreSQL dump:

```bash
docker-compose exec postgres pg_dump -U lectionseller lectionseller > backup.sql
```

If `DATABASE_USER` or `DATABASE_NAME` are changed, replace the values in the command.

Upload files are stored in the Docker volume `uploads_data`.

## Useful Commands

Migrations:

```bash
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web alembic check
```

Create or update admin:

```bash
docker-compose run --rm web python -m app.cli.create_admin --username admin
```

Rebuild and restart services:

```bash
docker-compose build web bot
docker-compose up -d --force-recreate web bot
```

Logs:

```bash
docker-compose logs --tail=100 web
docker-compose logs --tail=100 bot
```

Stop project:

```bash
docker-compose down
```

Stop and delete volumes:

```bash
docker-compose down -v
```

`down -v` deletes the database, Redis data, and uploaded files.
