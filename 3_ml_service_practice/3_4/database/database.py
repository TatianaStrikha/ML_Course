import logging
import os
import sys
from pandas.io.formats.format import return_docstring
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, registry
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from contextlib import contextmanager, asynccontextmanager
import logging

logger = logging.getLogger("uvicorn.error")

# --- 1. Создание реестра и метаданных
mapper_registry = registry()

# Теперь можно получить метаданные
metadata = mapper_registry.metadata

# --- 2. Фабрика движка
def get_engine():
    """
    Возвращает один и тот же экземпляр движка.
    Создаётся при первом вызове.
    """
    if not hasattr(get_engine, "_engine"):
        from database.config import get_settings
        settings = get_settings()
        get_engine._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
    return get_engine._engine


# --- 3. Фабрика сессий
def get_session_local():
    """
    Возвращает один и тот же экземпляр async_sessionmaker.
    Создаётся при первом вызове.
    """
    if not hasattr(get_session_local, "_sessionmaker"):
        get_session_local._sessionmaker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return get_session_local._sessionmaker


# --- 4. Генератор сессии для FastAPI зависимостей
async def get_session():
    """
    Генератор сессии для использования в FastAPI зависимостях.
    Автоматически коммитит при успехе, откатывает при ошибке, закрывает в любом случае.
    """
    session = get_session_local()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# --- 5. Инициализация БД: принимает движок как аргумент
async def init_db(drop_all: bool = False, engine=None):
    """
    Инициализация базы данных: создание или удаление таблиц.
    Если engine не передан — использует get_engine().
    """
    engine = engine or get_engine()

    async with engine.begin() as conn:
        if drop_all:
            logger.info("Удаляем все существующие таблицы...")
            await conn.execute(text("SET session_replication_role = 'replica'"))
            await conn.run_sync(metadata.drop_all)
            await conn.execute(text("SET session_replication_role = 'origin'"))
            logger.info("Все таблицы удалены.")

        logger.info("Создаём таблицы...")
        await conn.run_sync(metadata.create_all)

    logger.info("База данных инициализирована.")

