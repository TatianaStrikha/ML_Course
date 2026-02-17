from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.user import user_router
from app.routes.balance import balance_router
from app.routes.ml_model import ml_model_router
from app.routes.ml_task import ml_task_router
from database.database import init_db
from database.config import get_settings
import uvicorn
import logging
from contextlib import asynccontextmanager
import sys, os
# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# logger = logging.getLogger(__name__)
logger = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.INFO)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация БД...")
    try:
        await init_db(drop_all=False)  # Асинхронная инициализация
        logger.info("БД успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {str(e)}")
        raise
    yield

    # Закрытие
    logger.info("Приложение закрывается...")


def create_application() -> FastAPI:
    """
    создание и настрока FastAPI
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Регистрация эндпоинтов
    # app.include_router(home_router, tags=['Home'])
    app.include_router(user_router, prefix='/users', tags=['Пользователи'])
    app.include_router(balance_router, prefix='/balance', tags=['Баланс'])
    app.include_router(ml_model_router, prefix='/ml_model', tags=['ML-модели'])
    app.include_router(ml_task_router, prefix='/ml_task', tags=['Запросы к ML-модели'])


    return app

app = create_application()



if __name__ ==  '__main__':
    # TODO:  запуск из командной строки
    #  Пр.   uvicorn api:app --reload --port 8899
    #          http://127.0.0.1:8899/
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(
        #'api:app',
        'app.api:app',
        host='localhost',  # '0.0.0.0'
        port=8080,
        reload=True,
        log_level="info"
    )


