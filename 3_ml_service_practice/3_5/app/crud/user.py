# =============================================
# Функции с пользователями для использования в эндпоинтах
# =============================================
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.balance import Balance
from app.crud.schemas import UserAuthSchema
from datetime import datetime
import logging
from app.auth.password_hash import PasswordHash


logger = logging.getLogger("uvicorn.error")


class UserCRUD:
    @staticmethod
    async def get_by_id(db_session: AsyncSession, user_id: int) -> User | None:
        """
        Поиск пользователя по ID. Только для is_deleted == False.
        """
        result = await db_session.execute(select(User).where(User.user_id == user_id, User.is_deleted == False))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db_session: AsyncSession, email: str) -> User | None:
        """
        Поиск пользователя по Email. Только для is_deleted == False.
        """
        result = await db_session.execute(select(User).where(User.email == email, User.is_deleted == False))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_any_by_id(db_session: AsyncSession, user_id: int) -> User | None:
        """
        Находит пользователя по ID в том числе удаленных
        """
        result = await db_session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_all(db_session: AsyncSession, limit: int | None = None, offset: int = 0):
        """Получение пользователей. Если limit=None, вернет всех."""
        query = select(User).where(User.is_deleted == False).offset(offset).limit(limit)
        result = await db_session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def create(db_session: AsyncSession, user_data: UserAuthSchema) -> User:
        """Создание нового пользователя с хешированием пароля.
            И создание баланса спривязкой к пользователю."""
        # Хешируем пароль
        password_hash = PasswordHash.create(user_data.password)
        # добавляем нового пользователя в БД
        new_user = User(
            user_name=user_data.user_name,
            email=user_data.email,
            password_hash=password_hash,
            registration_date=datetime.now()
        )
        #  создаем новый баланс в БД и привязываем к пользователю
        # благодаря relationship, user_id подставится автоматически после сохранения
        new_balance = Balance(amount=0.0, user=new_user)

        db_session.add(new_user)
        db_session.add(new_balance)

        await db_session.commit()
        await db_session.refresh(new_user)
        return new_user


    @staticmethod
    async def delete(db_session: AsyncSession, user_id: int) -> bool:
        """Удаление пользователя. Возвращает True, если удален, False если не найден.
            Проставляет флаг is_deleted=True
        """
        # 1. Сначала найдем пользователя, чтобы изменить его email
        user = await UserCRUD.get_by_id(db_session, user_id)
        if not user or user.is_deleted:
            return False

        # 2. Формируем новый "испорченный" email, чтобы освободить оригинальный
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        old_email = user.email
        new_email = f"del_{date_str}_{old_email}"

        # 3. Обновляем статус и email
        user.email = new_email
        user.is_deleted = True

        await db_session.commit()
        logger.info(f"Пользователь {user_id} удален (мягко). Email изменен: {old_email} -> {new_email}")
        return True


