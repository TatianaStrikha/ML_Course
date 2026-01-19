import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Any, Dict


# =============================================
# Перечисления
# =============================================
class UserRole(Enum):
    """Роли пользователей в системе."""
    USER = "user"
    ADMIN = "admin"

class TransactionType(Enum):
    """Типы финансовых транзакций."""
    TOP_UP = "top_up"  # пополнение депозита
    WITHDRAWAL = "withdrawal"  # cписание с депозита за запрос к ML
    REFUND = "refund"  # возврат средств, в случае сбоя модели

class TaskStatus(Enum):
    """Статусы выполнения ML-задачи."""
    WAITING = "Waiting"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    VALIDATION_ERROR = "ValidationError"


# =============================================
# Класс Пользователь
# =============================================
class User:
    def __init__(self, user_id: int, username: str, email: str, password_hash: str, role: UserRole = UserRole.USER):
        self._user_id = user_id
        self._username = username
        self._email = email
        self._password_hash = password_hash  # пароль должен храниться в хэшированном виде
        self._role = role
        self._balance = 0.0
        self._registration_date = datetime.datetime.now()

    # Геттеры для доступа к приватным полям
    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def balance(self) -> float:
        return self._balance

    def is_enough_balance(self, amount: float) -> bool:
        """Проверка достаточности средств на балансе."""
        if amount < 0:
            raise ValueError("Сумма для проверки не может быть отрицательной")
        return self._balance >= amount

    def update_balance(self, amount: float) -> bool:
        """Обновляет баланс пользователя. Возвращает True, если операция успешна.
             amount: положительное — пополнение, отрицательное — списание."""
        if self._balance + amount < 0:
            return False
        self._balance += amount
        return True

    def check_password(self, password_hash: str) -> bool:
        """Сравнивает переданный хэш пароля с хранимым."""
        # здесь должно быть безопасное сравнение хэшей
        return self._password_hash == password_hash


# =============================================
# Класс Модель Машинного Обучения
# =============================================
class MLModel:
    def __init__(self, model_id: int, name: str, cost_per_prediction: float, description: str = ""):
        self._model_id = model_id
        self._name = name
        self._cost_per_prediction = cost_per_prediction # цена за одно предсказание
        self._description = description

    @property
    def model_id(self) -> int:
        return self._model_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def cost_per_prediction(self) -> float:
        return self._cost_per_prediction

    @property
    def description(self) -> str:
        return self._description


# =============================================
# Класс Транзакций (для истории операций с балансом)
# =============================================
class Transaction:
    def __init__(self, transaction_id: int, user: User, amount: float, transaction_type: TransactionType, description: str = "", related_task_id: Optional[int] = None):
        self._transaction_id = transaction_id
        self._user = user
        self._amount = amount
        self._type = transaction_type
        self._description = description
        self._timestamp = datetime.datetime.now()
        self._related_task_id = related_task_id  # ссылка на MLTask

    @property
    def transaction_id(self) -> int:
        return self._transaction_id

    @property
    def user(self) -> User:
        return self._user

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def type(self) -> TransactionType:
        return self._type

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def related_task_id(self) -> Optional[int]:
        return self._related_task_id


# =============================================
# Класс Задача ML (основная бизнес-сущность)
# =============================================
class MLTask:
    def __init__(self, task_id: int, user: User, model: MLModel, input_data: Dict[str, Any]):
        self._task_id = task_id
        self._user = user
        self._model = model
        self._input_data = input_data  # данные для предсказания
        self._status = TaskStatus.WAITING
        self._prediction_result: Optional[Dict[str, Any]] = None  # выдаёт либо словарь, либо None
        self._validation_errors: List[str] = []
        self._created_at = datetime.datetime.now()
        self._processed_at: Optional[datetime.datetime] = None
        self._transaction: Optional[Transaction] = None  # связь с транзакцией списания

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def user(self) -> User:
        return self._user

    @property
    def cost(self) -> float:
        return self._model.cost_per_prediction

    @property
    def status(self) -> TaskStatus:
        return self._status

    def validate_balance(self) -> bool:
        """Проверяет, достаточно ли у пользователя средств для выполнения задачи."""
        if not self._user.is_enough_balance(self.cost):
            self._validation_errors.append(f"Недостаточно средств: требуется {self.cost}, доступно {self._user.balance}")
            self._status = TaskStatus.FAILED
            return False
        return True


    def validate_data(self) -> bool:
        """Валидация входных данных. Возвращает True, если данные валидны."""
        self._validation_errors = []  # Сброс ошибок перед новой проверкой

        # проверка наличия данных
        if not self._input_data:
            self._validation_errors.append("Введите данные")
            self._status = TaskStatus.VALIDATION_ERROR
            return False

        # Здесь будет реализована логика валидации, специфичная для модели
        # (проверка наличия обязательных полей, типов данных)

        # если ошибок нет, данные считаются валидными
        return True


    def execute(self) -> bool:
        """Выполняет задачу, если баланс положительный и данные валидны."""
        if not self.validate_balance():
            return False

        if not self.validate_data():
            return False

        # если проверки пройдены, списываем средства и создаем транзакцию
        if self._user.update_balance(-self.cost):
            # Создаём транзакцию списания
            self._transaction = Transaction(
                transaction_id=hash((self._task_id, self._user.user_id, self._created_at.timestamp())),
                user=self._user,
                amount=-self.cost,
                transaction_type=TransactionType.WITHDRAWAL,
                description=f"Оплата за предсказание модели {self._model.name}",
                related_task_id=self._task_id
            )

            self._status = TaskStatus.IN_PROGRESS
            return True
        else:
            self._status = TaskStatus.FAILED
            self._validation_errors.append("Ошибка при списании средств")
            return False

    def set_result(self, prediction_result: Dict[str, Any], is_success: bool = True):
        """ Устанавливает результат выполнения задачи. Только если задача в статусе IN_PROGRESS.
        При неудаче — автоматически возвращает деньги на баланс пользователя."""
        if self._status != TaskStatus.IN_PROGRESS:
            raise RuntimeError(f"Нельзя установить результат для задачи в статусе {self._status.value}")

        self._processed_at = datetime.datetime.now()

        if is_success:
            self._prediction_result = prediction_result
            self._status = TaskStatus.COMPLETED
            self._error_reason = None  # Очистить, если успех
        else:
            #  сбой модели, возвращаем деньги
            self._status = TaskStatus.FAILED
            self._error_reason = "Неизвестная ошибка при обработке модели"

        # Убеждаемся, что деньги были списаны
        if self._transaction and self._transaction.amount < 0:
            refund_amount = -self._transaction.amount  # Положительная сумма для возврата
            #  возврат средств на баланс
            self._user.update_balance(refund_amount)
            # Создаём транзакцию возврата
            self._refund_transaction = Transaction(
                transaction_id=hash((self._task_id, self._user.user_id, self._processed_at.timestamp(), "refund")),
                user=self._user,
                amount=refund_amount,
                transaction_type=TransactionType.REFUND,
                description=f"Возврат средств за неудачное предсказание модели {self._model.name}. Причина: {self._error_reason}",
                related_task_id=self._task_id
            )
            self._refund_amount = refund_amount


    def get_result(self) -> Optional[Dict[str, Any]]:
        """Возвращает результат предсказания."""
        return self._prediction_result

    def get_validation_errors(self) -> List[str]:
        """Возвращает список ошибок валидации."""
        return self._validation_errors.copy()

    def get_transaction(self) -> Optional[Transaction]:
        """Возвращает транзакцию, связанную с этой задачей (если есть)."""
        return self._transaction

# =============================================
# Интерфейсы для взаимодействия
# =============================================
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


# =============================================
# Реализация REST API интерфейса
# =============================================
class RestAPIInterface(Interface):
    """Реализация интерфейса для REST API."""

    def register_user(self, username: str, email: str, password: str) -> User:
        """ Логика регистрации через REST
           Генерация user_id, хэширование пароля и т.д."""
        pass

    # ... Реализация остальных методов

# =============================================
# Реализация TelegramBot интерфейса
# =============================================
class TelegramBotInterface(Interface):
    """Реализация интерфейса для Telegram Bot."""

    def register_user(self, username: str, email: str, password: str) -> User:
        # Логика регистрации через бота (может отличаться)
        pass


    # ... Реализация остальных методов ...




if __name__ == '__main__':
    user = User(user_id=1, username="user111", email="user@123.ru", password_hash="123")
    print(user.username)