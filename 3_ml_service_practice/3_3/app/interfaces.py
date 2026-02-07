# =============================================
# Интерфейсы для взаимодействия
# =============================================
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from user import User
from transaction import Transaction
from ml_task import MLTask

class Interface(ABC):
    """Абстрактный класс для взаимодействия с пользователем."""

    # регистрация
    @abstractmethod
    def register_user(self, username: str, email: str, password: str) -> User:
        pass

    # аутентификация
    @abstractmethod
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        pass

     # отправить запрос к модели
    @abstractmethod
    def submit_prediction_request(self, user: User, model_id: int, data: Dict[str, Any]) -> MLTask:
        pass

    # посмотреть баланс
    @abstractmethod
    def get_user_balance(self, user: User) -> float:
        pass

    # пополнить баланс
    @abstractmethod
    def deposit_funds(self, user: User, amount: float) -> bool:
        pass

    # история транзакций
    @abstractmethod
    def get_transaction_history(self, user: User) -> List[Transaction]:
        pass

    # история запросов к модели
    @abstractmethod
    def get_prediction_history(self, user: User) -> List[MLTask]:
        pass