# LectionSeller TG Bot

English | [Русский](README.md)

A Telegram bot and web-admin panel for selling pharmacology lectures and educational materials.

LectionSeller TG Bot combines a course catalog, payments, automatic access delivery, a Telegram-based user cabinet, and an administrative web interface for managing educational content.

## Purpose

The project is designed for teachers, course authors, and educational teams that need a manageable way to sell digital materials through Telegram.

Users interact with the bot: open the catalog, choose a lecture or a block, pay for the purchase, and receive access to the materials inside Telegram. Administrators manage catalog structure, pricing, files, users, payments, and support requests through the web interface.

## User Features

- Telegram bot main menu.
- Catalog hierarchy: `Section -> Block -> Lecture`.
- Lecture and block cards with descriptions and prices.
- Single lecture purchases.
- Full block purchases.
- YooKassa payment flow.
- Manual payment status check from Telegram.
- Automatic access delivery after successful payment.
- "My Purchases" section.
- Purchased content visibility only after database access verification.
- Delivery of PDF, video, audio, image, and text materials.
- Support request flow.
- Static "About" section.

## Admin Panel

The web-admin panel allows project management without direct database access:

- admin authentication;
- statistics dashboard;
- section management;
- block management;
- lecture management;
- material upload and editing;
- price and activity management;
- user overview;
- purchase overview;
- payment overview;
- support request overview;
- manual access granting;
- manual access revocation.

## Payments And Access

Payment logic is isolated in a dedicated service layer. YooKassa is used as the current payment provider.

After payment confirmation, the system:

1. marks the purchase as paid;
2. creates access grants for related lectures;
3. stores payment data and raw payload;
4. shows materials to the user in the "My Purchases" section.

Repeated webhook notifications and repeated payment checks are processed idempotently.

## Content Delivery

Materials are attached to specific lectures. Supported content types:

- PDF;
- video;
- audio;
- images;
- text materials.

Files can be stored on the server or delivered through `telegram_file_id`.

## Content Protection

The project uses the strongest practical protection measures available within Telegram:

- content delivery only after database access verification;
- no public material links;
- backend-controlled file storage;
- content delivery inside the bot;
- `protect_content=True` for Telegram messages and files;
- local file path validation;
- content delivery logging.

Important: Telegram cannot fully prevent downloads, screen recording, screen photos, or modified clients. The project restricts standard forwarding and unauthorized access, but it is not a DRM system.

## Architecture

The project is built as a layered application:

- `bot` - Telegram handlers, keyboards, FSM, and middleware;
- `web` - FastAPI routes, admin panel, webhooks;
- `services` - business logic;
- `repositories` - data access layer;
- `db.models` - SQLAlchemy models;
- `config` - Pydantic Settings;
- `common` - shared enums, logging, and security helpers;
- `cli` - service commands.

Business logic is kept separate from Telegram handlers and web routes. This improves testing, maintainability, and extensibility.

## Technology Stack

- Python 3.12
- aiogram 3.x
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Redis
- YooKassa SDK
- Pydantic Settings
- Jinja2
- Docker
- Docker Compose

## Documentation

- [Russian setup and deployment guide](docs/SETUP.ru.md)
- [Production deployment for tracerxbrhd.ru](docs/DEPLOY.tracerxbrhd.ru.md)
- [Telegram Mini App plan](docs/MINIAPP_PLAN.ru.md)
- [Setup and deployment guide](docs/SETUP.en.md)

## License

This project is distributed under a proprietary license. Use, copying, modification, distribution, publication, sublicensing, or commercial exploitation of the source code is prohibited without prior written permission from the copyright holder.

See [LICENSE](LICENSE).
