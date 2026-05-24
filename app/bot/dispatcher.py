from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import catalog, menu, payments, start, support
from app.bot.middlewares.db import DbSessionMiddleware
from app.config.settings import get_settings


def create_dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    dispatcher = Dispatcher(storage=RedisStorage.from_url(get_settings().redis_url))
    dispatcher.message.middleware(DbSessionMiddleware(session_factory))
    dispatcher.callback_query.middleware(DbSessionMiddleware(session_factory))
    dispatcher.include_router(start.router)
    dispatcher.include_router(catalog.router)
    dispatcher.include_router(payments.router)
    dispatcher.include_router(support.router)
    dispatcher.include_router(menu.router)
    return dispatcher
