# =============================================
# Перечисления
# =============================================
from enum import Enum

class UserRole(Enum):
    """Роли пользователей в системе."""
    USER = "user"
    ADMIN = "admin"

class TransactionType(Enum):
    """Типы финансовых транзакций."""
    TOP_UP = "top_up"  # пополнение баланса
    SPEND = "spend"  # cписание с баланса
    REFUND = "refund"  # возврат средств, в случае сбоя модели

class TaskStatus(Enum):
    """Статусы выполнения ML-задачи."""
    WAITING = "Waiting"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    VALIDATION_ERROR = "ValidationError"
