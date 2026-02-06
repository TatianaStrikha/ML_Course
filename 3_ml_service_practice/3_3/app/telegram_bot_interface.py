# =============================================
# Реализация TelegramBot интерфейса
# =============================================
from interfaces import Interface
from user import User

class TelegramBotInterface(Interface):
    """Реализация интерфейса для Telegram Bot."""

    def register_user(self, username: str, email: str, password: str) -> User:
        # Логика регистрации через бота (может отличаться)
        pass


    # ... Реализация остальных методов ...
