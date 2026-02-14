# =============================================
# Класс Транзакций (для истории операций с балансом)
# =============================================
import datetime
from database.database import Base
from enums import UserRole, TaskStatus, TransactionType
from typing import List, Optional, Any, Dict
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship


class Transaction(Base):
     __tablename__ = 'transactions'
     transaction_id = Column(Integer, primary_key=True, autoincrement=True)
     user_id = Column(Integer, ForeignKey('users.user_id'))
     amount = Column(Numeric(precision=15, scale=2))
     transaction_type = Column(Enum(TransactionType))
     description = Column(String(255))
     created_at = Column(DateTime, default=datetime.datetime.now)
     related_task_id = Column(Integer, ForeignKey('ml_tasks.task_id'))
     # Связь с пользователем (ORM-связь с классом User)
     user = relationship("User", back_populates="transactions")
     # Связь с MLTask
     ml_tasks = relationship("MLTask", back_populates="transactions")


     def top_up_balance(user, amount: float, description: str = "Пополнение баланса") :
         """ Пополнение баланса
         """
         if amount <= 0:
                    raise ValueError("Сумма пополнения должна быть положительной")

         # SQLAlchemy сам добавит транзакцию в сессию (если transaction  добавлена в сессию session.add(transaction))
         transaction = Transaction(
                    user=user,
                    amount=amount,
                    transaction_type=TransactionType.TOP_UP,
                    description=description,
                    related_task_id=None
         )
         return  transaction

     def spend_balance(user, amount: float, description: str = "Списание с баланса") :
         """ Списание денег с баланса пользователя
         """
         if amount <= 0:
                    raise ValueError("Сумма списания должна быть положительной")

         # SQLAlchemy сам добавит транзакцию в сессию (если transaction  добавлена в сессию session.add(transaction))
         transaction = Transaction(
                    user=user,
                    amount=amount,
                    transaction_type=TransactionType.SPEND,
                    description=description,
                    related_task_id=None
         )
         return  transaction