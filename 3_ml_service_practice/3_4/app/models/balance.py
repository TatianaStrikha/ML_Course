# =============================================
# ORM таблица Баланс
# =============================================
import datetime
from database.database import mapper_registry
from typing import List, Optional, Any, Dict
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship

@mapper_registry.mapped
class Balance:
     __tablename__ = 'balances'
     balance_id = Column(Integer, primary_key=True, autoincrement=True)
     user_id = Column(Integer, ForeignKey('users.user_id'))
     amount = Column(Numeric(precision=15, scale=2))
     # Связь с пользователем
     user = relationship("User", back_populates="balance")

