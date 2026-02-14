# =============================================
# Реализация REST API интерфейса
# =============================================
from interfaces import Interface
from user import User

class RestAPIInterface(Interface):
    """Реализация интерфейса для REST API."""

    def register_user(self, username: str, email: str, password: str) -> User:
        """ Логика регистрации через REST
           Генерация user_id, хэширование пароля и т.д."""
        pass

    # ... Реализация остальных методов