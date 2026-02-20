import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """ Класс берёт переменные из файла .env используя схему model_config
    """
    # параметры БД
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None

    APP_NAME: Optional[str] =  None
    APP_DESCRIPTION: Optional[str] =  None
    DEBUG: Optional[bool] = None
    API_VERSION: Optional[str] =None

    # параметры RabbitMQ
    RABBITMQ_USER: Optional[str] =  None
    RABBITMQ_PASS: Optional [str] =  None
    RABBITMQ_HOST: Optional[str] =  None
    RABBITMQ_PORT: Optional[int] =None

    # параметры токенов
    SECRET_KEY: Optional[str] =  None
    ALGORITHM: Optional[str] =  None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] =None

    @property
    def DATABASE_URL(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def RABBITMQ_URL(self) -> str:
        """Формирует строку подключения для aio-pika"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"


    # model_config - содержит путь к файлу env и берет от туда данные
    print("Текущий каталог:", os.getcwd())
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # чтобы Pydantic не ругался на лишние поля в .env
    )

@lru_cache()
def get_settings() -> Settings:
    """Получение настроек приложения с кэшированием"""
    settings = Settings()
    return settings
