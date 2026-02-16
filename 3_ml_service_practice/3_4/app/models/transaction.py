# =============================================
# ORM таблица Транзакций (для истории операций с балансом)
# =============================================
import datetime
from database.database import mapper_registry
from .enums import UserRole, TaskStatus, TransactionType
from typing import List, Optional, Any, Dict
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship

@mapper_registry.mapped
class Transaction:
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
