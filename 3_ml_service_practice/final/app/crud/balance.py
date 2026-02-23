# =============================================
# Функции с балансом для использования в эндпоинтах
# =============================================
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.balance import Balance
from datetime import datetime
from app.crud.user import UserCRUD
from decimal import Decimal
from app.models.transaction import Transaction
from app.models.enums import TransactionType
from sqlalchemy import select
import logging


logger = logging.getLogger("uvicorn.error")


class BalanceCRUD:
    @staticmethod
    async def get_active(db_session: AsyncSession, user_id: int) -> Balance | None:
        """
        Получение баланса только если пользователь существует и не удален.
        """
        # 1. Сбрасываем кэш сессии, чтобы увидеть изменения флага is_deleted
        db_session.expire_all()
        # 2. Проверяем пользователя
        user = await UserCRUD.get_by_id(db_session, user_id)
        # 3. Если пользователь не найден или удален (get_by_id вернет None)
        if not user:
            return None
        # 4. Если мы здесь, значит пользователь активен. Спокойно берем баланс.
        result = await db_session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_any(db_session: AsyncSession, user_id: int) -> Balance | None:
        """
        Получение баланса любого пользователя, в том числе удаленного.
        """
        result = await db_session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def top_up(db_session: AsyncSession, user_id: int, top_up_amount: Decimal) -> Balance:
        """
        Пополнение баланса и запись в историю транзакций.
        Только для неудаленнных пользователей.
        """
        # Получаем текущий баланс
        balance = await BalanceCRUD.get_active(db_session, user_id)
        if not balance:
            raise ValueError(f"Пользователь с id {user_id} не найден")

        # Сохраняем старый баланс для принта
        old_amount = balance.amount
        # Обновляем сумму
        balance.amount += top_up_amount

        # Создаем запись в таблице транзакций
        new_transaction = Transaction(
            user_id=user_id,
            amount= top_up_amount,
            transaction_type=TransactionType.TOP_UP,  # Используйте ваш Enum
            description=f"Пополнение баланса",
            created_at=datetime.now()
        )

        db_session.add(new_transaction)
        await db_session.commit()
        await db_session.refresh(balance)
        logger.info(f"Пополнение: {top_up_amount}, текущий баланс: {balance.amount}. Id пользователя {user_id}.")
        return balance

    @staticmethod
    async def get_user_transactions(db_session: AsyncSession, user_id: int):
        """
        История транзакций пользователя
        """
        result = await db_session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
        )
        return result.scalars().all()