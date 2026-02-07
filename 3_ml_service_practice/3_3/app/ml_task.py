# =============================================
# Класс Задача ML (основная бизнес-сущность)
# =============================================
import datetime
import time

from enums import UserRole, TaskStatus, TransactionType
from user import User
from typing import List, Optional, Any, Dict
from ml_model import MLModel
from transaction import Transaction
from database.database import Base
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship


class MLTask(Base):
    __tablename__ ='ml_tasks'
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    model_id = Column(Integer, ForeignKey('models.model_id'))
    input_data = Column(String) # данные для предсказания
    status = Column(Enum(TaskStatus))
    prediction_result=Column(String)
    created_at = Column(DateTime, default=datetime.datetime.now)

    #  связь с таблицей транзакций
    transactions = relationship("Transaction", back_populates="ml_tasks")

    def execute(self, user) -> bool:
        """Выполняет задачу, если баланс положительный и данные валидны."""
        # if not self.validate_balance():
        #     return False
        #
        # if not self.validate_data():
        #     return False

        # если проверки пройдены, списываем средства и создаем транзакцию
        # if self._balance.update(-self.cost):
        #    Создаём транзакцию списания
            # self._transaction = Transaction(
            #     transaction_id=hash((self._task_id, self._user.user_id, self._created_at.timestamp())),
            #     user=self._user,
            #     amount=-self.cost,
            #     transaction_type=TransactionType.SPEND,
            #     description=f"Оплата за предсказание модели {self._model.name}",
            #     related_task_id=self._task_id
            # )
            #self._status = TaskStatus.IN_PROGRESS
        # else:
        #     self._status = TaskStatus.FAILED
        #     self._validation_errors.append("Ошибка при списании средств")
        #     return False

        self._status = TaskStatus.IN_PROGRESS
        time.sleep(1)
        self.prediction_result = "prediction_result"
        return True