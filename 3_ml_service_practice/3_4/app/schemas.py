# =============================================
# Pydantic схемы
# =============================================
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from decimal import Decimal
from app.models.enums import TransactionType,TaskStatus


class UserAuthSchema(BaseModel):
    """
    Схема для регистрации/авторизации пользователей
    """
    user_name: str = Field(min_length=1, max_length=20)
    email: EmailStr #встроенная валидация емейла
    password: str = Field(min_length=6, max_length=20)
    # Позволяет Pydantic работать с SQLAlchemy моделями
    model_config = ConfigDict(from_attributes=True)


class UserReadSchema(BaseModel):
    """
    Схема для получения пользователей из БД
    """
    user_id: int
    user_name: str
    email: EmailStr
    registration_date: datetime
    model_config = ConfigDict(from_attributes=True)


class BalanceUpdateSchema(BaseModel):
    """
    Схема для проверки корректности суммы пополнения баланса
    gt=0 (Greater Than) -  запрещает пополнять баланс на 0 или отрицательные числа.
    """
    amount: Decimal = Field(gt=0, description="Сумма должна быть больше 0")


class BalanceCurrentSchema(BaseModel):
    """
    Схема для получения текущего баланса пользователя из БД
    """
    amount: Decimal
    model_config = ConfigDict(from_attributes=True)

class TransactionReadSchema(BaseModel):
    """
    Схема для полючения истории транзакций
    """
    transaction_id: int
    amount: Decimal
    transaction_type: TransactionType
    description: str | None
    created_at: datetime
    related_task_id: int | None
    model_config = ConfigDict(from_attributes=True)


class MLModelCreateSchema(BaseModel):
    """
    Схема для создания ML модели в БД
    """
    model_name: str = Field(..., min_length=2, max_length=50)
    cost_per_prediction: Decimal = Field(default=Decimal('0.00'), ge=0)
    description: str | None = None


class MLModelReadSchema(MLModelCreateSchema):
    """
    Схема для получения  ML модели из БД
    """
    model_id: int
    model_config = ConfigDict(from_attributes=True)


class MLTaskCreateSchema(BaseModel):
    """
    Схема для создания запроса к ML модели
    """
    user_id: int
    model_id: int
    input_data: str = Field(..., min_length=3, description="Данные для анализа")


class MLTaskReadSchema(BaseModel):
    """
    Схема для получения история запросов к ML-модели
    """
    task_id: int
    model_id: int
    input_data: str
    status: TaskStatus
    prediction_result: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)



