from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.user import user_router
from app.routers.balance import balance_router
from app.routers.ml_model import ml_model_router
from app.routers.ml_task import ml_task_router
from database.database import init_db
from config import get_settings
import uvicorn
import logging
from contextlib import asynccontextmanager
import sys, os
from fastapi.templating import Jinja2Templates
from app.routers.web import web_router
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# logger = logging.getLogger(__name__)
logger = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.INFO)
settings = get_settings()


templates = Jinja2Templates(directory="app/templates")



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация БД...")
    try:
        await init_db(drop_all=False)  # Асинхронная инициализация
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
    app.include_router(user_router, prefix='/users', tags=['Пользователи'])
    app.include_router(balance_router, prefix='/balance', tags=['Баланс'])
    app.include_router(ml_model_router, prefix='/ml_model', tags=['ML-модели'])
    app.include_router(ml_task_router, prefix='/ml_task', tags=['Запросы к ML-модели'])
    app.include_router(web_router, tags=["Web-интерфейс"])

    @app.exception_handler(status.HTTP_401_UNAUTHORIZED)
    async def unauthorized_exception_handler(request: Request, exc: HTTPException):
        """Редирект на страницу входа, в случае отсутсвия токена в куках. Только для web-интерфейса"""
        # Список путей, которые относятся к веб-интерфейсу (HTML)
        protected_pages = ["profile"]

        # Проверяем, содержит ли текущий URL хотя бы одно слово из списка
        if any(page in request.url.path for page in protected_pages):
            # Перенаправляем браузер на страницу входа
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        # Для всех остальных случаев (Swagger/API) возвращаем стандартный JSON

        # Для обычного REST API (Swagger) возвращаем стандартный JSON
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.detail},
        )


    return app

app = create_application()



if __name__ ==  '__main__':
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(
        'app.api:app',
        host='localhost',  # '0.0.0.0'
        port=8080,
        reload=True,
        log_level="info"
    )


