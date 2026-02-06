import psycopg2
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # параметры
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None

    APP_NAME: Optional[str] =  None
    DEBUG: Optional[bool] = None
    API_VERSION: Optional[str] =None
    
    @property
    def DATABASE_URL_psycopg(self):
        return f'postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
    
    # model_config - содержит путь к файлу env, откуда берет данные для подключения к бд
    print("Текущий каталог:", os.getcwd())
    model_config = SettingsConfigDict(
        env_file="./database/.env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

def get_settings() -> Settings:
    settings = Settings()
    return settings
