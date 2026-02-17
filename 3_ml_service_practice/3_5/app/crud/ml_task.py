# =============================================
# Функции с ML тасками для использования в эндпоинтах
# =============================================
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.balance import Balance
from app.models.transaction import Transaction
from app.models.ml_model import MLModel
from app.models.ml_task import MLTask
from app.models.enums import TransactionType,TaskStatus


class MLTaskCRUD:
    @staticmethod
    async def create(
            db_session: AsyncSession,
            user_id: int,
            model_id: int,
            input_data: str
    ) -> MLTask:
        """
        Инициализация задачи: проверка баланса, списание средств.
        """
        # 1. Получаем модель и её стоимость
        model_result = await db_session.execute(select(MLModel).where(MLModel.model_id == model_id))
        ml_model = model_result.scalar_one_or_none()
        if not ml_model:
            raise ValueError("Модель не найдена")

        # 2. Проверяем баланс пользователя
        balance_result = await db_session.execute(select(Balance).where(Balance.user_id == user_id))
        balance = balance_result.scalar_one_or_none()

        if not balance or balance.amount < ml_model.cost_per_prediction:
            raise ValueError("Недостаточно средств на балансе")

        # 3. Валидация входных данных (заглушка)
        if len(input_data) < 3:  # Пример: текст слишком короткий
            raise ValueError("Ошибка валидации данных: текст слишком короткий")

        # 4. Списание средств
        balance.amount -= ml_model.cost_per_prediction

        # 5. Создаем задачу и транзакцию SPEND. Статус WAITING - задача ушла в очередь, но ещё не принята воркером.
        new_task = MLTask(
            user_id=user_id,
            model_id=model_id,
            input_data=input_data,
            status=TaskStatus.WAITING,
            created_at=datetime.now()
        )
        db_session.add(new_task)
        await db_session.flush()  # Чтобы получить task_id для транзакции

        new_transaction = Transaction(
            user_id=user_id,
            amount=-ml_model.cost_per_prediction,  # Отрицательное число для списания
            transaction_type=TransactionType.SPEND,
            description=f"Списание за ML-модель {ml_model.model_name}",
            related_task_id=new_task.task_id
        )
        db_session.add(new_transaction)

        await db_session.commit()
        await db_session.refresh(new_task)
        return new_task

    @staticmethod
    async def update_status(db_session: AsyncSession, task_id: int, status: TaskStatus):
        """
        Обновление статуса задачи (например, на InProgress).
        """
        result = await db_session.execute(select(MLTask).where(MLTask.task_id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            # не делаем commit здесь, так как сессией управляет воркер


    @staticmethod
    async def complete_task(db_session: AsyncSession, task_id: int, result_data: str):
        """
        Завершение задачи с сохранением результата.
        """
        result = await db_session.execute(select(MLTask).where(MLTask.task_id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = TaskStatus.COMPLETED
            task.prediction_result = result_data
            task.completed_at = datetime.now()




    @staticmethod
    async def refund(db_session: AsyncSession, task_id: int, error_message: str):
        """
        Возврат средств в случае сбоя модели (REFUND).
        """
        task_result = await db_session.execute(
            select(MLTask).where(MLTask.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task or task.status == TaskStatus.FAILED:
            return

        # Получаем стоимость из модели через задачу
        model_result = await db_session.execute(select(MLModel).where(MLModel.model_id == task.model_id))
        ml_model = model_result.scalar_one()

        # Возвращаем деньги на баланс
        balance_result = await db_session.execute(select(Balance).where(Balance.user_id == task.user_id))
        balance = balance_result.scalar_one()
        balance.amount += ml_model.cost_per_prediction

        # Обновляем статус задачи
        task.status = TaskStatus.FAILED
        task.prediction_result = f"Error: {error_message}"

        # Создаем транзакцию возврата
        refund_transaction = Transaction(
            user_id=task.user_id,
            amount=ml_model.cost_per_prediction,
            transaction_type=TransactionType.REFUND,
            description=f"Возврат средств за задачу № {task.task_id}",
            related_task_id=task.task_id
        )
        db_session.add(refund_transaction)
        await db_session.commit()


    @staticmethod
    async def get_history(db_session: AsyncSession, user_id: int):
        """
        Список всех ML-запросов пользователя (от новых к старым)
        """
        result = await db_session.execute(
            select(MLTask)
            .where(MLTask.user_id == user_id)
            .order_by(MLTask.created_at.desc())
        )
        return result.scalars().all()


