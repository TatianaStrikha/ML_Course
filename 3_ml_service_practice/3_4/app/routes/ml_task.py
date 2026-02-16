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


logger = logging.getLogger("uvicorn.error")
ml_task_router = APIRouter()


@ml_task_router.post("/predict", summary="Запуск ML-предсказания")
async def run_prediction(
        task_data: MLTaskCreateSchema,
        db_session: AsyncSession = Depends(get_session)
):
    """
    **Процесс работы эндпоинта:**
    1. Валидация и списание средств (SPEND).
    2. Имитация работы модели (2 секунды).
    3. Случайный сбой (10%) -> Возврат средств (REFUND).
    4. Успех -> Запись результата.
    """
    try:
        # 1: Создаем задачу и списываем деньги
        task = await MLTaskCRUD.create(
            db_session,
            user_id=task_data.user_id,
            model_id=task_data.model_id,
            input_data=task_data.input_data
        )

        # 2: Имитация работы ML-модели
        await asyncio.sleep(2)

        # 3: Симуляция случайной ошибки (шанс 10%)
        if random.random() < 0.1:
            await MLTaskCRUD.refund(db_session, task.task_id, "Внутренняя ошибка нейросети")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Модель дала сбой. Средства возвращены на баланс."
            )

        # 4: Успешное завершение
        task.status = TaskStatus.COMPLETED
        task.prediction_result = f"Предсказание для: {task_data.input_data[:10]}... [OK]"

        await db_session.commit()

        return {
            "task_id": task.task_id,
            "status": task.status,
            "result": task.prediction_result
        }

    except ValueError as e:
        # Сюда попадут ошибки "Недостаточно средств" или "Модель не найдена"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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