# =============================================
# ORM таблица Пользователи
# =============================================
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from database.database import mapper_registry

@mapper_registry.mapped
class User:
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100))
    email = Column(String)
    password_hash = Column(String)
    registration_date = Column(DateTime)
    is_deleted = Column(Boolean, default=False)  # флаг об удалении
    # ORM-связь с классом Transaction
    transactions = relationship("Transaction", back_populates="user")
    balance = relationship("Balance", back_populates="user")


