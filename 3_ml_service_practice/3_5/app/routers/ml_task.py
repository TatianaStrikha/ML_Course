from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from app.crud.ml_task import MLTaskCRUD
from app.crud.ml_model import MLModelCRUD
from app.crud.schemas import MLTaskReadSchema
from app.models.enums import TaskStatus
import logging
from app.crud.user import UserCRUD
import json
from datetime import datetime
from aio_pika import connect, Message
from config import get_settings
from app.auth.access_token import get_current_user
from app.models.user import User
from fastapi.security import APIKeyCookie
from app.crud.schemas import MLTaskCreateSchema

# Указываем FastAPI, что мы используем куку с именем access_token
cookie_sec = APIKeyCookie(name="access_token", auto_error=False)

logger = logging.getLogger("uvicorn.error")
ml_task_router = APIRouter()

async def send_to_rabbit(task_id: int, input_text: str, model_id: int):
    """Функция для работы с очередью"""
    settings = get_settings()
    payload = {
        "task_id": str(task_id),
        "features": {"input": input_text},
        "model": model_id,
        "timestamp": datetime.now().isoformat()
    }
    connection = await connect(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue("ml_tasks", durable=True)
        await channel.default_exchange.publish(
            Message(json.dumps(payload).encode()),
            routing_key="ml_tasks"
        )

@ml_task_router.post("/predict", summary="Запуск ML-предсказания", dependencies=[Depends(cookie_sec)])
async def run_prediction(
        input_data: MLTaskCreateSchema,
        db_session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user) # получения объекта User из кук
):
    """
    **Механизм работы эндпоинта:**
    - Работает только для авторизованного пользователя.
    - user_id берется из кук, id модели по умолчанию 1
    - Проверка достаточности средств.
    - Валидация данных.
    - Задача передается в очередь -> списание средств со счета.
    - Забирается воркером.
    - Сохранения результата в БД.
    """
    try:
        # получаем актуальную модель из БД
        active_model = await MLModelCRUD.get_first_model(db_session)
        # Создаем задачу в БД со статусом WAITING (деньги спишутся внутри CRUD)
        task = await MLTaskCRUD.create(
            db_session,
            user_id=current_user.user_id, # ID из кук
            model_id=active_model.model_id,
            input_data=input_data.input_data
        )

        # Отправка в очередь
        await send_to_rabbit(task.task_id, input_data.input_data, active_model.model_id)

        # Возвращаем ответ сразу, не дожидаясь завершения задачи
        return {
            "task_id": task.task_id,
            "status": TaskStatus.WAITING,
            "message": "Задача поставлена в очередь"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@ml_task_router.get(
    "/{task_id}",
    response_model=MLTaskReadSchema,
    summary="Получение информации о задаче по id"
)
async def get_task(task_id: int,db_session: AsyncSession = Depends(get_session)):
    task = await MLTaskCRUD.get_by_id(db_session, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    return task



@ml_task_router.get(
    "/history/{user_id}",
    response_model=list[MLTaskReadSchema],
    summary="Получить историю ML-запросов пользователя"
)
async def get_history(user_id: int, db_session: AsyncSession = Depends(get_session)):
    """
    Список ML-запросов любого пользователя, в том числе удаленного.
    """
    # Проверяем физическое наличие пользователя в БД
    user = await UserCRUD.get_any_by_id(db_session, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Пользователь с id {user_id} никогда не существовал"
        )

    #  Получаем транзакции
    history = await MLTaskCRUD.get_history(db_session, user_id)

    #  пометка о статусе пользователя в консоль
    status = "УДАЛЕН" if user.is_deleted else "АКТИВЕН"
    logger.info(f"История ML-запросов пользователя с id {user_id} ({status}): найдено {len(history)} записей")

    return history


