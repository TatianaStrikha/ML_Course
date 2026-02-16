# =============================================
# ORM таблица ML таски
# =============================================
import datetime
import time

from .enums import UserRole, TaskStatus, TransactionType
#from user import User
from typing import List, Optional, Any, Dict
from database.database import mapper_registry
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship

@mapper_registry.mapped
class MLTask:
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
