# Production Deployment: tracerxbrhd.ru

Документ описывает деплой LectionSeller TG Bot на Ubuntu 24.04 VPS с доменами:

- `tracerxbrhd.ru`
- `www.tracerxbrhd.ru`
- `api.tracerxbrhd.ru`

## Production-Архитектура

```text
Internet
  |
  | HTTPS 443 / HTTP 80
  v
Nginx на VPS
  |
  | proxy_pass http://127.0.0.1:8000
  v
Docker Compose
  |- web: FastAPI admin/webhooks/health
  |- bot: aiogram polling process
  |- postgres: internal DB only
  |- redis: internal FSM storage only
```

Выбор:

- Nginx установлен на хосте, а не в Docker, чтобы проще выпускать и обновлять SSL через Certbot.
- `web` публикуется только на `127.0.0.1:8000`, наружу он недоступен напрямую.
- `bot` работает отдельным контейнером и не зависит от HTTP-трафика.
- PostgreSQL и Redis не публикуют порты наружу.

## DNS

В DNS-зоне домена добавьте A-записи:

| Host | Type | Value |
| --- | --- | --- |
| `tracerxbrhd.ru` или `@` | `A` | `<VPS_IPV4>` |
| `www.tracerxbrhd.ru` или `www` | `A` | `<VPS_IPV4>` |
| `api.tracerxbrhd.ru` или `api` | `A` | `<VPS_IPV4>` |

Если у VPS есть IPv6, можно дополнительно добавить AAAA-записи:

| Host | Type | Value |
| --- | --- | --- |
| `tracerxbrhd.ru` или `@` | `AAAA` | `<VPS_IPV6>` |
| `www.tracerxbrhd.ru` или `www` | `AAAA` | `<VPS_IPV6>` |
| `api.tracerxbrhd.ru` или `api` | `AAAA` | `<VPS_IPV6>` |

Проверка DNS:

```bash
dig +short tracerxbrhd.ru
dig +short www.tracerxbrhd.ru
dig +short api.tracerxbrhd.ru
```

## Первый Запуск На Чистом VPS

```bash
sudo apt-get update
sudo apt-get install -y git
git clone <REPOSITORY_URL> ~/lectionseller-tg-bot
cd ~/lectionseller-tg-bot
chmod +x scripts/*.sh
./scripts/server-install-ubuntu.sh
```

Если пользователь был добавлен в группу `docker`, перелогиньтесь в SSH.

## ENV

```bash
cd ~/lectionseller-tg-bot
cp .env.example .env
nano .env
```

Заполнить вручную:

```text
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_SECRET_KEY=<long-random-secret>
BASE_URL=https://tracerxbrhd.ru
ALLOWED_HOSTS=tracerxbrhd.ru,www.tracerxbrhd.ru,api.tracerxbrhd.ru,localhost,127.0.0.1

BOT_TOKEN=<telegram-bot-token>
ADMIN_TELEGRAM_IDS=<telegram-admin-id>

DATABASE_NAME=lectionseller
DATABASE_USER=lectionseller
DATABASE_PASSWORD=<strong-db-password>
DATABASE_ECHO=false

REDIS_DB=0
REDIS_PASSWORD=

WEB_BIND_HOST=127.0.0.1
WEB_PORT=8000

YOOKASSA_SHOP_ID=<shop-id>
YOOKASSA_SECRET_KEY=<secret-key>
YOOKASSA_RETURN_URL=https://tracerxbrhd.ru/payments/return
YOOKASSA_WEBHOOK_ALLOWED_IPS=

UPLOAD_DIR=uploads
```

Сгенерировать `APP_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Docker Compose Deploy

```bash
cd ~/lectionseller-tg-bot
./scripts/server-deploy.sh
```

Создать администратора:

```bash
CREATE_ADMIN=1 ADMIN_USERNAME=admin ./scripts/server-deploy.sh
```

Заполнить демо-каталог:

```bash
SEED_DEMO_CATALOG=1 ./scripts/server-deploy.sh
```

## Nginx

Установочный скрипт ставит `nginx`. Скопируйте конфиг:

```bash
sudo cp deploy/nginx/tracerxbrhd.ru.conf /etc/nginx/sites-available/tracerxbrhd.ru.conf
sudo ln -sfn /etc/nginx/sites-available/tracerxbrhd.ru.conf /etc/nginx/sites-enabled/tracerxbrhd.ru.conf
sudo nginx -t
sudo systemctl reload nginx
```

Проверить HTTP до Certbot:

```bash
curl -I http://tracerxbrhd.ru/health
curl -I http://www.tracerxbrhd.ru/health
curl -I http://api.tracerxbrhd.ru/health
```

## HTTPS Через Certbot

Установить Certbot через snap:

```bash
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sfn /snap/bin/certbot /usr/bin/certbot
```

Выпустить сертификат и включить HTTPS redirect:

```bash
sudo certbot --nginx \
  -d tracerxbrhd.ru \
  -d www.tracerxbrhd.ru \
  -d api.tracerxbrhd.ru \
  --redirect
```

Проверить auto-renew:

```bash
sudo certbot renew --dry-run
```

## YooKassa

Return URL:

```text
https://tracerxbrhd.ru/payments/return
```

Webhook URL:

```text
https://tracerxbrhd.ru/payments/webhooks/yookassa
```

Можно также использовать:

```text
https://api.tracerxbrhd.ru/payments/webhooks/yookassa
```

Если используете `api.tracerxbrhd.ru` для webhook, укажите тот же URL в кабинете YooKassa. Приложение принимает оба домена, потому что они проксируются на один FastAPI service.

## Проверка После Деплоя

Контейнеры:

```bash
docker compose ps
```

Web:

```bash
curl -f https://tracerxbrhd.ru/health
curl -I https://tracerxbrhd.ru/admin/login
```

Nginx:

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo tail -n 100 /var/log/nginx/lectionseller.error.log
```

SSL:

```bash
curl -I https://tracerxbrhd.ru
sudo certbot certificates
sudo certbot renew --dry-run
```

Bot:

```bash
docker compose logs --tail=100 bot
```

В логах должно быть:

```text
Starting Telegram bot polling.
Run polling for bot ...
```

YooKassa config внутри контейнера:

```bash
docker compose exec bot python -c "from app.config.settings import get_settings; s=get_settings(); print('yookassa_enabled=', s.yookassa_enabled); print('return_url=', s.yookassa_return_url)"
```

## Обновление

```bash
cd ~/lectionseller-tg-bot
git pull
./scripts/server-deploy.sh
sudo nginx -t
sudo systemctl reload nginx
```

## Важные Замечания По Безопасности

- `.env` не коммитить.
- `APP_DEBUG=false` в production.
- `APP_SECRET_KEY` должен быть длинным случайным значением.
- `DATABASE_PASSWORD` должен быть сильным.
- `WEB_BIND_HOST=127.0.0.1`, чтобы FastAPI был доступен только через Nginx.
- PostgreSQL и Redis не должны быть опубликованы наружу.
- `ALLOWED_HOSTS` должен содержать только реальные домены и localhost для healthcheck.
- Админка использует signed HttpOnly cookie, `SameSite=Lax`, `Secure` в production и Origin/Referer guard для POST/PUT/PATCH/DELETE запросов.
- UFW должен разрешать SSH, 80/tcp и 443/tcp.

Открыть firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```
