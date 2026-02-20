from passlib.context import CryptContext

# Создаем контекст с использованием bcrypt алгоритма
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordHash:
    """
    Класс для хеширования и верификации паролей с использованием bcrypt.
    """
    @staticmethod
    def create(password: str) -> str:
        """
        Создает хеш из переданного пароля.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.
        """
        return pwd_context.verify(password, password_hash)