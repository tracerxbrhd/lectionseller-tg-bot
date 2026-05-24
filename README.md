# LectionSeller TG Bot

Telegram-бот и web-admin panel для продажи лекций и обучающих материалов по фармакологии.

Проект рассчитан на запуск 24/7 на VPS через Docker Compose. В составе есть Telegram-бот на aiogram 3, FastAPI admin panel, PostgreSQL, Redis, Alembic и интеграция YooKassa.

## Возможности

- Каталог: разделы -> блоки -> лекции.
- Покупка отдельной лекции или блока.
- YooKassa checkout: создание платежа, ссылка оплаты, webhook, ручная кнопка проверки оплаты.
- Автоматическая выдача `AccessGrant` после успешной оплаты.
- Раздел "Мои покупки" в Telegram.
- Выдача PDF, видео, аудио, изображений и текстовых материалов.
- `protect_content=True` для материалов, где это включено в админке.
- Поддержка пользователей с сохранением обращений в БД и уведомлением администраторов в Telegram.
- Web-admin panel: управление каталогом, материалами, пользователями, покупками, платежами, обращениями и доступами.
- Docker Compose для локального запуска и деплоя.

## Стек

- Python 3.12
- aiogram 3.x
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Redis
- YooKassa SDK
- Pydantic Settings
- Docker + Docker Compose

## Структура

```text
app/
  bot/
    handlers/        Telegram handlers
    keyboards/       Reply/inline keyboards
    middlewares/     DB session middleware
    states/          FSM states
  cli/               service commands
  common/            enums, logging, security helpers
  config/            Pydantic settings
  db/
    models/          SQLAlchemy models
    repositories/    DB access layer
    session.py       async engine/session factory
  services/
    access/          access grants
    catalog/         catalog read logic
    content/         purchased content delivery logic
    payments/        payment abstraction + YooKassa
    purchases/       purchase creation
    support/         support requests
    users/           user registration/update
  web/
    admin/           FastAPI admin routes
    routers/         public web routes and webhooks
    static/
    templates/
alembic/             DB migrations
```

Логика разделена по слоям:

- `handlers` принимают Telegram/web события и отвечают пользователю.
- `services` содержат бизнес-логику.
- `repositories` изолируют SQLAlchemy-запросы.
- `models` описывают схему БД.
- `payments` сделан через абстрактный payment service, чтобы позже добавить другого провайдера или подписки.

## ENV

Секреты хранятся только в `.env`. Файл `.env` исключен из git. Перед production-деплоем замените все dev/test значения, включая Telegram bot token, `APP_SECRET_KEY`, пароли БД и ключ YooKassa.

Скопируйте пример:

```powershell
Copy-Item .env.example .env
```

Основные переменные:

| Переменная | Назначение |
| --- | --- |
| `APP_ENV` | `local`, `production` или другое имя окружения. |
| `APP_DEBUG` | Debug режим FastAPI. В production поставить `false`. |
| `APP_LOG_LEVEL` | Уровень логирования: `INFO`, `WARNING`, `ERROR`. |
| `APP_SECRET_KEY` | Секрет для signed admin session cookie. Должен быть длинным случайным значением. |
| `BASE_URL` | Публичный URL web-сервиса, например `https://example.com`. |
| `BOT_TOKEN` | Токен Telegram-бота от BotFather. |
| `ADMIN_TELEGRAM_IDS` | Telegram ID админов через запятую для уведомлений поддержки. |
| `DATABASE_*` | Настройки PostgreSQL. |
| `REDIS_*` | Настройки Redis. |
| `WEB_PORT` | Порт web/admin сервиса на хосте. |
| `YOOKASSA_SHOP_ID` | ID магазина YooKassa. |
| `YOOKASSA_SECRET_KEY` | Секретный ключ YooKassa. |
| `YOOKASSA_RETURN_URL` | URL страницы возврата после оплаты. |
| `YOOKASSA_WEBHOOK_ALLOWED_IPS` | Опциональный allowlist IP/CIDR для webhook YooKassa. |
| `UPLOAD_DIR` | Каталог хранения загруженных файлов внутри контейнера. |

Сгенерировать `APP_SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Локальный Запуск

Быстрый запуск на локальной Windows-машине:

```powershell
.\scripts\local-start.ps1
```

Первый запуск создаст `.env` из `.env.example`, если файла ещё нет. Заполните секреты и повторите команду.

Полезные флаги:

```powershell
.\scripts\local-start.ps1 -CreateAdmin
.\scripts\local-start.ps1 -SeedDemoCatalog
.\scripts\local-start.ps1 -Rebuild
.\scripts\local-start.ps1 -SkipBuild
.\scripts\local-start.ps1 -SkipMigrations
```

Ручной запуск:

1. Подготовьте `.env`:

```powershell
Copy-Item .env.example .env
```

2. Заполните минимум:

```text
BOT_TOKEN=...
APP_SECRET_KEY=...
ADMIN_TELEGRAM_IDS=...
```

3. Соберите и запустите инфраструктуру:

```powershell
docker-compose build
docker-compose up -d postgres redis
```

4. Примените миграции:

```powershell
docker-compose run --rm web alembic upgrade head
```

5. Создайте администратора:

```powershell
docker-compose run --rm web python -m app.cli.create_admin --username admin
```

Команда запросит пароль интерактивно. Не используйте слабые пароли.

6. Запустите bot и web:

```powershell
docker-compose up -d web bot
```

7. Проверьте сервисы:

```powershell
docker-compose ps
docker-compose logs --tail=80 bot
docker-compose logs --tail=80 web
```

Healthcheck:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

Админка:

```text
http://localhost:8000/admin/login
```

## Работа С Контентом

1. Войдите в админку.
2. Создайте раздел.
3. Создайте блок внутри раздела и укажите цену блока.
4. Создайте лекции внутри блока и укажите цены лекций.
5. Добавьте материалы лекции во вкладке "Материалы".
6. Для файлов можно использовать upload, локальный `file_path` или `telegram_file_id`.
7. Включите `protected_content_enabled`, если нужно запретить штатную пересылку сообщения средствами Telegram.

Файлы, загруженные через админку, хранятся в Docker volume `uploads_data` и доступны bot/web контейнерам по `UPLOAD_DIR`.

## YooKassa

В `.env` укажите:

```text
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
YOOKASSA_RETURN_URL=https://example.com/payments/return
```

Webhook endpoint:

```text
https://example.com/payments/webhooks/yookassa
```

В личном кабинете YooKassa добавьте HTTP-уведомления на этот URL. Для локальной разработки нужен публичный HTTPS-туннель, например ngrok или cloudflared.

Если webhook недоступен в тестовом окружении, пользователь может нажать кнопку "Проверить оплату" в Telegram. Бот запросит статус платежа у YooKassa и выдаст доступ, если платеж уже `succeeded`.

Webhook обработчик идемпотентен: повторное уведомление не должно создавать повторную выдачу доступа в рамках одной покупки.

## Покупки И Доступ

Поддерживаются:

- покупка лекции;
- покупка блока целиком.

Покупка раздела и подписки заложены архитектурно через `PurchaseType`, но не включены в пользовательском сценарии как полноценная production-фича.

После успешной оплаты:

1. `Purchase` переводится в `paid`;
2. создаются `AccessGrant` для доступных лекций;
3. пользователь видит материалы в "Мои покупки";
4. при каждом открытии материала доступ проверяется по БД.

Если одна лекция куплена отдельно и дополнительно входит в купленный блок, это нормально: у пользователя может быть несколько активных источников доступа к одной лекции.

## Поддержка

Пользователь открывает "Поддержка" в боте и отправляет вопрос.

Система:

- сохраняет обращение в `support_requests`;
- отправляет уведомление Telegram-админам из `ADMIN_TELEGRAM_IDS`;
- показывает обращения в админке;
- позволяет менять статус обращения.

## Защита Контента В Telegram

Telegram не позволяет на 100% запретить:

- скачивание;
- запись экрана;
- копирование;
- фотографирование экрана;
- пересылку любыми обходными способами.

В проекте реализованы максимально доступные меры:

- `protect_content=True` при отправке материалов, если включено у `ContentItem`;
- доступ к материалам только после проверки `AccessGrant`;
- отсутствие публичных ссылок на материалы;
- выдача файлов только внутри бота;
- хранение upload-файлов под контролем backend в Docker volume;
- проверка пути файла, чтобы нельзя было выйти за пределы `UPLOAD_DIR`;
- логирование факта выдачи материала пользователю.

Для критически ценных материалов дополнительно используйте водяные знаки, персонализацию PDF/видео, лимиты выдачи и юридические условия доступа.

## VPS Deployment

Минимальная схема:

- VPS с Docker и Docker Compose;
- домен;
- reverse proxy с HTTPS, например Nginx, Caddy или Traefik;
- закрытый доступ к PostgreSQL и Redis снаружи;
- регулярные backup PostgreSQL и upload volume.

Быстрый путь для Ubuntu 24.04:

```bash
chmod +x scripts/server-install-ubuntu.sh scripts/server-deploy.sh
./scripts/server-install-ubuntu.sh
```

После установки Docker перелогиньтесь в SSH, если скрипт добавил пользователя в группу `docker`.

Затем подготовьте `.env`:

```bash
cp .env.example .env
nano .env
```

Минимум для production:

```text
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<long-random-secret>
BASE_URL=https://example.com
BOT_TOKEN=<telegram-bot-token>
DATABASE_PASSWORD=<strong-db-password>
YOOKASSA_SHOP_ID=<shop-id>
YOOKASSA_SECRET_KEY=<secret-key>
YOOKASSA_RETURN_URL=https://example.com/payments/return
```

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

`scripts/server-install-ubuntu.sh` ставит Docker Engine и Docker Compose plugin через официальный apt repository Docker для Ubuntu. Такой способ выбран вместо convenience script, потому что официальный Docker convenience script сам помечен как вариант для testing/development, а для production Docker рекомендует apt repository.

Дополнительные опции install script:

```bash
CONFIGURE_FIREWALL=1 ./scripts/server-install-ubuntu.sh
REMOVE_CONFLICTING_DOCKER_PACKAGES=1 ./scripts/server-install-ubuntu.sh
```

`CONFIGURE_FIREWALL=1` откроет `OpenSSH`, `80/tcp`, `443/tcp` и включит UFW. Используйте только если понимаете текущие правила firewall на сервере.

Ручной путь:

Шаги:

1. Скопируйте проект на сервер.
2. Создайте `.env` из `.env.example`.
3. Установите production значения:

```text
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<long-random-secret>
BASE_URL=https://example.com
YOOKASSA_RETURN_URL=https://example.com/payments/return
WEB_PORT=8000
```

4. Соберите и запустите:

```bash
docker-compose build
docker-compose up -d postgres redis
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web python -m app.cli.create_admin --username admin
docker-compose up -d web bot
```

5. Настройте reverse proxy:

```text
https://example.com -> http://127.0.0.1:8000
```

6. В YooKassa укажите webhook:

```text
https://example.com/payments/webhooks/yookassa
```

7. Проверьте:

```bash
docker-compose ps
docker-compose logs --tail=100 web
docker-compose logs --tail=100 bot
curl -f https://example.com/health
```

## Backup

PostgreSQL dump:

```bash
docker-compose exec postgres pg_dump -U lectionseller lectionseller > backup.sql
```

Если в `.env` изменены `DATABASE_USER` или `DATABASE_NAME`, замените значения в команде.

Upload-файлы лежат в Docker volume `uploads_data`. Для production настройте регулярное копирование этого volume или используйте внешнее объектное хранилище в будущей версии.

## Полезные Команды

Миграции:

```powershell
docker-compose run --rm web alembic upgrade head
docker-compose run --rm web alembic check
```

Создать или обновить администратора:

```powershell
docker-compose run --rm web python -m app.cli.create_admin --username admin
```

Заполнить демо-каталог разделами, блоками и лекциями:

```powershell
.\scripts\seed-demo-catalog.ps1
```

То же самое на Linux/VPS:

```bash
./scripts/seed-demo-catalog.sh
```

Команда идемпотентна: повторный запуск обновляет найденные записи по названию, а не создаёт дубли. Материалы к лекциям она не добавляет, файлы прикрепляются отдельно через админку.

Пересобрать и перезапустить сервисы:

```powershell
docker-compose build web bot
docker-compose up -d --force-recreate web bot
```

Логи:

```powershell
docker-compose logs --tail=100 web
docker-compose logs --tail=100 bot
```

Остановить проект:

```powershell
docker-compose down
```

Остановить с удалением volumes:

```powershell
docker-compose down -v
```

Команда `down -v` удаляет БД, Redis и загруженные файлы. Используйте только если точно хотите стереть локальные данные.

## Проверка Перед Production

- Заменить development Telegram bot token.
- Установить сильный `APP_SECRET_KEY`.
- Установить сильный пароль PostgreSQL.
- `APP_DEBUG=false`.
- Проверить HTTPS для домена.
- Проверить webhook YooKassa.
- Проверить backup БД и upload volume.
- Создать админа с сильным паролем.
- Проверить, что `.env` не попадает в git.
- Проверить выдачу PDF/видео/аудио/изображения/текста через Telegram.
