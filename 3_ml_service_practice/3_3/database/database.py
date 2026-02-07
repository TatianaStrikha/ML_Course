import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

# Создаём базовый класс для всех моделей
Base = declarative_base()

# Отложенный импорт настроек
def get_settings():
    from database.config import get_settings as _get_settings
    return _get_settings()


def get_database_engine():
    """ Создаёт и настраивает движок SQLAlchemy для подключения к PostgreSQL.
    Возвращает: Engine - настроенный движок SQLAlchemy
    """
    settings = get_settings()  # Получаем настройки внутри функции
    engine = create_engine(
        url=settings.DATABASE_URL_psycopg,
        echo=settings.DEBUG,  # Выводить SQL-запросы в лог (только для разработки)
        pool_size=5,  # Количество соединений в пуле
        max_overflow=10,  # Максимум дополнительных соединений при перегрузке
        pool_pre_ping=True,  # Проверять соединение перед использованием
        pool_recycle=3600,  # Перезапуск соединения каждые 3600 секунд (1 час)
    )
    return engine

def get_session_local():
    """ функция создания сессии"""
    engine = get_database_engine()
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

@contextmanager
def get_session():
    """ Контекстный менеджер для работы с сессией БД.
    """
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db(drop_all: bool = False) -> None:
    """ Инициализирует схему базы данных.
    """
    try:
        engine = get_database_engine()

        if drop_all:
            print("Удаляем все существующие таблицы...")
            #  каскадное удаление
            with engine.begin() as conn:
                # временное отключение проверки внешних ключей
                conn.execute(text("SET session_replication_role = 'replica'"))
                #  удаление всех таблиц
                Base.metadata.drop_all(conn)
                # Включение проверки внешних ключей обратно
                conn.execute(text("SET session_replication_role = 'origin'"))
        # создание таблиц в БД на базе наших объектов (User, Balance, Transaction  и др.)
        print("Создаём таблицы...")
        Base.metadata.create_all(engine)
        print("Схема базы данных успешно инициализирована!")
        return engine  # Возвращаем engine для использования в main.py

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise

