import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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

    # Параметры RabbitMQ
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672

    @property
    def DATABASE_URL(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def RABBITMQ_URL(self) -> str:
        """Формирует строку подключения для aio-pika"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"


    # model_config - содержит путь к файлу env, откуда берет данные для подключения к бд
    print("Текущий каталог:", os.getcwd())
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # чтобы Pydantic не ругался на лишние поля в .env
    )

def get_settings() -> Settings:
    settings = Settings()
    return settings
