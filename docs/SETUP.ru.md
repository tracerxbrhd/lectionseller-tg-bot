# Запуск И Деплой

[English](SETUP.en.md) | Русский

Этот документ содержит эксплуатационные инструкции для локального запуска, серверного деплоя и обслуживания LectionSeller TG Bot.

## ENV

Секреты хранятся только в `.env`. Файл `.env` исключен из git.

Создать `.env`:

```powershell
Copy-Item .env.example .env
```

На Linux/VPS:

```bash
cp .env.example .env
```

Основные переменные:

| Переменная | Назначение |
| --- | --- |
| `APP_ENV` | Окружение: `local`, `production` или другое значение. |
| `APP_DEBUG` | Debug режим FastAPI. |
| `APP_LOG_LEVEL` | Уровень логирования. |
| `APP_SECRET_KEY` | Секрет signed admin session cookie. |
| `BASE_URL` | Публичный URL web-сервиса. |
| `ALLOWED_HOSTS` | Разрешенные HTTP Host заголовки для web-сервиса. |
| `BOT_TOKEN` | Токен Telegram-бота. |
| `ADMIN_TELEGRAM_IDS` | Telegram ID администраторов через запятую. |
| `DATABASE_*` | Настройки PostgreSQL. |
| `REDIS_*` | Настройки Redis. |
| `WEB_BIND_HOST` | Host/IP, на котором порт web-сервиса публикуется на сервере. Для production с Nginx: `127.0.0.1`. |
| `WEB_PORT` | Порт web/admin сервиса на хосте. |
| `YOOKASSA_SHOP_ID` | ID магазина YooKassa. |
| `YOOKASSA_SECRET_KEY` | Секретный ключ YooKassa. |
| `YOOKASSA_RETURN_URL` | URL возврата после оплаты. |
| `YOOKASSA_WEBHOOK_ALLOWED_IPS` | Allowlist IP/CIDR для webhook YooKassa. |
| `UPLOAD_DIR` | Каталог хранения загруженных файлов внутри контейнера. |

Сгенерировать `APP_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Локальный Запуск

Быстрый запуск на Windows:

```powershell
.\scripts\local-start.ps1
```

Полезные флаги:

```powershell
.\scripts\local-start.ps1 -CreateAdmin
.\scripts\local-start.ps1 -SeedDemoCatalog
.\scripts\local-start.ps1 -Rebuild
.\scripts\local-start.ps1 -SkipBuild
.\scripts\local-start.ps1 -SkipMigrations
```

Ручной запуск:

```powershell
docker-compose build
docker-compose up -d postgres redis
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web python -m app.cli.create_admin --username admin
docker-compose up -d web bot
```

Проверка:

```powershell
docker-compose ps
docker-compose logs --tail=80 web
docker-compose logs --tail=80 bot
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

Админка:

```text
http://localhost:8000/admin/login
```

## Демо-Каталог

Заполнить демо-каталог разделами, блоками и лекциями:

```powershell
.\scripts\seed-demo-catalog.ps1
```

Проверить без записи в БД:

```powershell
.\scripts\seed-demo-catalog.ps1 -DryRun
```

На Linux/VPS:

```bash
./scripts/seed-demo-catalog.sh
```

Команда идемпотентна: повторный запуск обновляет найденные записи по названию, а не создает дубли. Материалы к лекциям она не добавляет.

## Ubuntu 24.04 VPS

Быстрая установка системных зависимостей:

```bash
chmod +x scripts/server-install-ubuntu.sh scripts/server-deploy.sh
./scripts/server-install-ubuntu.sh
```

Если скрипт добавил пользователя в группу `docker`, перелогиньтесь в SSH.

Подготовить `.env`:

```bash
cp .env.example .env
nano .env
```

Минимум для production:

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

Подробная инструкция для домена `tracerxbrhd.ru`: [DEPLOY.tracerxbrhd.ru.md](DEPLOY.tracerxbrhd.ru.md).

Деплой:

```bash
./scripts/server-deploy.sh
```

Создать администратора во время деплоя:

```bash
CREATE_ADMIN=1 ADMIN_USERNAME=admin ./scripts/server-deploy.sh
```

Заполнить демо-каталог во время деплоя:

```bash
SEED_DEMO_CATALOG=1 ./scripts/server-deploy.sh
```

## YooKassa

Webhook endpoint:

```text
http://<SERVER_IP>:8000/payments/webhooks/yookassa
```

Для стабильной production-работы рекомендуется HTTPS-домен. Без домена и HTTPS можно использовать ручную кнопку "Проверить оплату" в Telegram: бот сам запросит статус платежа у YooKassa и выдаст доступ при успешной оплате.

## Обновление На Сервере

```bash
cd ~/lectionseller-tg-bot
git pull
./scripts/server-deploy.sh
```

Если есть локальные изменения:

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

Если изменены `DATABASE_USER` или `DATABASE_NAME`, замените значения в команде.

Upload-файлы находятся в Docker volume `uploads_data`.

## Полезные Команды

Миграции:

```bash
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web alembic check
```

Создать или обновить администратора:

```bash
docker-compose run --rm web python -m app.cli.create_admin --username admin
```

Пересобрать и перезапустить сервисы:

```bash
docker-compose build web bot
docker-compose up -d --force-recreate web bot
```

Логи:

```bash
docker-compose logs --tail=100 web
docker-compose logs --tail=100 bot
```

Остановить проект:

```bash
docker-compose down
```

Остановить с удалением volumes:

```bash
docker-compose down -v
```

`down -v` удаляет БД, Redis и загруженные файлы.
