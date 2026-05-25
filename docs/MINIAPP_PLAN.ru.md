# Telegram Mini App: План И API-Контракт

Этот документ фиксирует поэтапную реализацию Telegram Mini App для LectionSeller TG Bot.

Mini App дополняет существующего Telegram-бота и web-admin panel, но не заменяет их.
Текущая бизнес-логика остается в сервисном слое Python-приложения:
каталог, покупки, платежи, доступы и поддержка должны переиспользовать
существующие services/repositories.

## Цели

- Открывать приложение внутри Telegram по URL `https://tracerxbrhd.ru/app`.
- Дублировать пользовательский функционал бота: каталог, покупки, оплата, мои материалы, поддержка.
- Добавить admin mode для Telegram-администраторов.
- Дать администратору возможность отвечать на обращения пользователей.
- Сохранить текущий FastAPI backend, PostgreSQL, Redis, YooKassa и Docker Compose.

## Выбранный Стек

Frontend:

- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- lucide-react
- Telegram WebApp JS API

Backend:

- FastAPI routes `/miniapp/api/*`
- Telegram Mini App `initData` validation
- текущие SQLAlchemy models/repositories/services
- текущий YooKassa payment layer

## URL И Routing

Frontend:

```text
GET /app
```

API:

```text
GET  /miniapp/api/meta
GET  /miniapp/api/auth/me
GET  /miniapp/api/catalog/sections
GET  /miniapp/api/catalog/sections/{section_id}/blocks
GET  /miniapp/api/catalog/blocks/{block_id}/lectures
POST /miniapp/api/purchases
POST /miniapp/api/payments/{purchase_id}/check
GET  /miniapp/api/purchases/my
GET  /miniapp/api/content/lectures/{lecture_id}
POST /miniapp/api/support/requests
GET  /miniapp/api/support/requests
GET  /miniapp/api/admin/support/requests
POST /miniapp/api/admin/support/requests/{request_id}/reply
```

На текущем этапе реализованы рабочие backend endpoints:

```text
GET /miniapp/api/meta
GET /miniapp/api/auth/me
GET /miniapp/api/catalog/sections
GET /miniapp/api/catalog/sections/{section_id}/blocks
GET /miniapp/api/catalog/blocks/{block_id}/lectures
POST /miniapp/api/purchases
POST /miniapp/api/payments/{purchase_id}/check
GET /miniapp/api/purchases/my
GET /miniapp/api/content/lectures/{lecture_id}
GET /miniapp/api/content/items/{content_item_id}/file
POST /miniapp/api/support/requests
GET /miniapp/api/support/requests
```

Остальные endpoints подключены как явные заглушки `501 planned`, чтобы зафиксировать
контракт и не смешивать этапы реализации.

Локальный frontend dev server:

```text
frontend/miniapp
npm install
npm run dev
```

Vite proxy отправляет `/miniapp/api/*` на `http://127.0.0.1:8000`.

## Авторизация Mini App

Frontend получает `Telegram.WebApp.initData` и отправляет его в backend в заголовке:

```text
X-Telegram-Init-Data: <initData>
```

Backend авторизация реализована на этапе 3:

1. проверить подпись `initData` через `BOT_TOKEN`;
2. проверить свежесть `auth_date`;
3. достать Telegram user payload;
4. создать или обновить `User`;
5. запретить доступ заблокированным пользователям;
6. определить `is_admin` через `ADMIN_TELEGRAM_IDS` и поле пользователя.

Клиент не должен доверять `initDataUnsafe` для авторизации. Это только удобный источник данных для UI.

## Контент И Файлы

Mini App не должен отдавать публичные ссылки на материалы.

Для материалов будут использоваться защищенные endpoints:

- backend проверяет Telegram initData;
- backend проверяет `AccessGrant`;
- backend выдает файл или текст только при активном доступе;
- для PDF/image/text возможен inline preview;
- для video/audio нужен защищенный streaming endpoint на следующем этапе контента.

Telegram и webview не дают полной DRM-защиты от скачивания или записи экрана.
Поэтому задача backend — исключить публичную выдачу и проверять доступ
перед каждым материалом.

## Поддержка И Ответы Админа

Текущая модель `SupportRequest` хранит одно сообщение пользователя. Для полноценного
диалога потребуется отдельная миграция на одном из следующих этапов:

```text
SupportMessage
- id
- support_request_id
- sender_type: user/admin/system
- user_id
- admin_id
- message
- created_at
```

Это позволит:

- показывать историю обращения пользователю;
- отвечать администратору из Mini App;
- отвечать из web-admin panel;
- отправлять пользователю Telegram-уведомление о новом ответе.

## Этапы

1. Архитектурный каркас и API-контракт.
2. React/Vite frontend scaffold.
3. Backend авторизация через Telegram initData.
4. Кнопка открытия Mini App в Telegram-боте.
5. Каталог в Mini App.
6. Покупки и YooKassa flow.
7. Мои покупки и защищенный просмотр материалов.
8. Пользовательская поддержка.
9. Docker production build frontend.
10. Admin mode: очередь обращений и ответы.
11. Расширение web-admin support dialog.
12. QA, дизайн-полировка, проверка платежей и доступов.

## Текущий Статус

Готово на этапе 1:

- настройка `MINIAPP_URL`;
- route `/app` с временной страницей;
- route `/miniapp/api/meta`;
- API-заглушки для следующих этапов;
- схемы API-ответов;
- placeholder dependency для будущей проверки `X-Telegram-Init-Data`.

Готово на этапе 2:

- React/Vite/TypeScript/Tailwind scaffold в `frontend/miniapp`;
- Telegram WebApp helper: `ready`, `expand`, theme params, haptic tap, `initData`;
- API client с заголовком `X-Telegram-Init-Data`;
- mobile-first layout с вкладками: каталог, покупки, поддержка, админ;
- loading/error/success состояния подключения к `/miniapp/api/meta`;
- placeholder UI для следующих этапов без подключения к реальным данным.

Готово на этапе 3:

- сервис проверки Telegram Mini App `initData`;
- HMAC SHA256 validation по `BOT_TOKEN`;
- проверка `auth_date` через `MINIAPP_INIT_DATA_MAX_AGE_SECONDS`;
- dependency `require_miniapp_user`;
- dependency `require_miniapp_admin`;
- endpoint `GET /miniapp/api/auth/me`;
- upsert пользователя в `users`;
- запрет Mini App API для заблокированных пользователей;
- админские Mini App endpoints требуют `is_admin`.

Готово на этапе 4:

- reply-кнопка `Открыть приложение` в главном меню бота;
- inline-кнопка `Открыть приложение` в каталоге;
- inline-кнопка `Открыть приложение` в разделе покупок;
- fallback handler на текст `Открыть приложение`;
- установка Telegram menu button через `set_chat_menu_button`;
- защита local/dev: WebApp-кнопки добавляются только для `https://` URL.

Готово на этапе 5:

- Mini App API каталога подключен к текущему `CatalogService`;
- endpoint `GET /miniapp/api/catalog/sections` возвращает активные разделы;
- endpoint `GET /miniapp/api/catalog/sections/{section_id}/blocks` возвращает активные блоки раздела;
- endpoint `GET /miniapp/api/catalog/blocks/{block_id}/lectures` возвращает активные лекции блока;
- frontend каталог загружает данные через TanStack Query вместо mock-данных;
- реализована навигация `Раздел -> Блок -> Лекция` внутри Mini App;
- добавлены состояния загрузки, ошибки и пустого каталога;
- кнопки покупки пока не активны, они будут подключены на этапе YooKassa flow.

Готово на этапе 6:

- endpoint `POST /miniapp/api/purchases` создает pending purchase через текущий `PurchaseService`;
- создание платежной ссылки переиспользует `CheckoutService` и `YooKassaPaymentService`;
- endpoint `POST /miniapp/api/payments/{purchase_id}/check` проверяет оплату через `PaymentConfirmationService`;
- успешная проверка оплаты переиспользует текущую выдачу `AccessGrant`;
- frontend Mini App показывает платежный блок с кнопками `Открыть оплату` и `Проверить оплату`;
- ошибки YooKassa логируются на backend и отображаются пользователю как управляемое состояние;
- покупка блока и отдельной лекции работает через единый API-контракт.

Готово на этапе 7:

- endpoint `GET /miniapp/api/purchases/my` возвращает купленные лекции через `ContentLibraryService`;
- endpoint `GET /miniapp/api/content/lectures/{lecture_id}` возвращает материалы только после проверки `AccessGrant`;
- endpoint `GET /miniapp/api/content/items/{content_item_id}/file` отдает локальный файл только при активном доступе;
- файловый endpoint не раскрывает прямые пути и требует Telegram Mini App `initData`;
- frontend `Мои покупки` загружает реальные купленные лекции;
- frontend показывает материалы лекции: text inline, PDF/image/video/audio через backend blob preview;
- материалы с `telegram_file_id` помечаются как доступные через бота, пока backend file source отсутствует.

Готово на этапе 8:

- endpoint `POST /miniapp/api/support/requests` создает обращение через текущий `SupportService`;
- endpoint `GET /miniapp/api/support/requests` возвращает историю обращений пользователя;
- создание обращения из Mini App уведомляет Telegram-администраторов через `BOT_TOKEN`;
- frontend `Поддержка` отправляет вопрос, показывает статус отправки и ошибки;
- frontend показывает историю обращений со статусами `open`, `in_progress`, `closed`;
- полноценный диалог с ответами администратора остается следующим этапом admin support mode.

Готово на этапе 9:

- Vite собирает production assets с base path `/app/`;
- Dockerfile собирает Mini App frontend в отдельном Node build stage;
- runtime Python image получает только готовый `frontend/miniapp/dist`;
- FastAPI отдает Mini App на `/app`, `/app/` и будущих SPA routes;
- FastAPI отдает Vite assets через `/app/assets/*`;
- при отсутствии frontend build `/app` возвращает управляемый `503`, а не пустую страницу.

Для production нужно, чтобы `MINIAPP_URL` был публичным HTTPS URL:

```text
MINIAPP_URL=https://tracerxbrhd.ru/app
```

Также в BotFather нужно настроить Main Mini App / домен бота для `tracerxbrhd.ru`.
Официальная документация Telegram перечисляет запуск Mini Apps из keyboard button,
inline button и bot menu button: https://core.telegram.org/bots/webapps
