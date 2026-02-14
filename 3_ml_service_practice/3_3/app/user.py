# =============================================
# Класс Пользователь
# =============================================
from database.database import Base
from enums import UserRole, TaskStatus, TransactionType
from sqlalchemy import Column, Integer, String, Enum, Float, Numeric
from decimal import Decimal
from sqlalchemy.orm import relationship
from transaction import Transaction


class User(Base):
    # название таблицы в БД, которая будет создаваться при вызове Base.metadata.create_all(engine)
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100))
    email = Column(String)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    # balance = Column(Numeric(precision=15, scale=2), default=Decimal(0.0))
    registration_date = Column(String)  #datetime.datetime.now()
    # ORM-связь с классом Transaction
    transactions = relationship("Transaction", back_populates="user")
    balance = relationship("Balance", back_populates="user")


    def check_password(self, password_hash: str) -> bool:
        """Сравнивает переданный хэш пароля с хранимым."""
        # здесь должно быть безопасное сравнение хэшей
        return self._password_hash == password_hash

    def get_balance(self) :
        """
        """
        return self.balance


