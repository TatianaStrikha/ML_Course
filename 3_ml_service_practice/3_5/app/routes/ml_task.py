import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from app.crud.ml_task import MLTaskCRUD
from app.schemas import MLTaskCreateSchema, MLTaskReadSchema
from app.models.enums import TaskStatus
import logging
from app.crud.user import UserCRUD
import json
from datetime import datetime
from aio_pika import connect, Message
from config import get_settings


logger = logging.getLogger("uvicorn.error")
ml_task_router = APIRouter()


@ml_task_router.post("/predict", summary="Запуск ML-предсказания")
async def run_prediction(
        task_data: MLTaskCreateSchema,
        db_session: AsyncSession = Depends(get_session)
):
    """
    **Механизм работы эндпоинта:**
    - Проверка достаточности средств.
    - Валидация данных (заглушка).
    - Задача передается в очередь -> списание средств со счета.
    - Забирается воркером.
    - Иммитация работы (sleep(2)).
    - Симуляция сбоя 10% -> возврат средств на счет.
    - Сохранения результата в БД.
    """
    try:
        # 1: Создаем задачу в БД со статусом WAITING (деньги спишутся внутри CRUD)
        task = await MLTaskCRUD.create(
            db_session,
            user_id=task_data.user_id,
            model_id=task_data.model_id,
            input_data=task_data.input_data
        )

        # 2: Подготовка сообщения для RabbitMQ
        payload = {
            "task_id": str(task.task_id),
            "features": {"input": task_data.input_data},
            "model": task_data.model_id,
            "timestamp": datetime.now().isoformat()
        }

        # 3: Отправка в RabbitMQ
        settings = get_settings()
        connection = await connect(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # durable=True — очередь сохранится после перезагрузки RabbitMQ
            await channel.declare_queue("ml_tasks", durable=True)

            await channel.default_exchange.publish(
                Message(json.dumps(payload).encode()),
                routing_key="ml_tasks"
            )

        # 4: Возвращаем ответ сразу, не дожидаясь ML
        return {
            "task_id": task.task_id,
            "status": TaskStatus.WAITING,
            "message": "Задача поставлена в очередь"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


