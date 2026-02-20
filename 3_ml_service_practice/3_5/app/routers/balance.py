from fastapi import APIRouter, HTTPException, Depends
from app.crud.balance import BalanceCRUD
from app.crud.user import UserCRUD
from  database.database import get_session
import logging
from app.crud.schemas import BalanceUpdateSchema, BalanceCurrentSchema, TransactionReadSchema
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger("uvicorn.error")

# Объявляем роутер, к которому привязываем маршруты
balance_router = APIRouter()



@balance_router.get(
   "/{user_id}",
   response_model=BalanceCurrentSchema,
   summary="Получить баланс"
)
async def get(user_id: int, db_session: AsyncSession = Depends(get_session)):
    """
    Просмотр текущего баланса активного пользователя.
    """
    balance = await BalanceCRUD.get_active(db_session, user_id)
    if not balance:
        raise HTTPException(status_code=404, detail="Баланс не найден")
    return balance


@balance_router.post(
   "/top_up/{user_id}",
   response_model=BalanceCurrentSchema,
   summary="Пополнить баланс"
)
async def top_up(
    user_id: int,
    deposit_data: BalanceUpdateSchema,
    db_session: AsyncSession = Depends(get_session)
):
    """
    **Пополнение баланса.**
    - Позволяет провести операцию только для активных пользователей (is_deleted=False).
    - Автоматически создает запись в истории транзакций.
    """
    try:
       # Передаем сумму из схемы в метод
       return await BalanceCRUD.top_up(db_session, user_id, deposit_data.amount)
    except ValueError as e:
       raise HTTPException(status_code=404, detail=str(e))


@balance_router.get(
    "/transactions/{user_id}",
    response_model=list[TransactionReadSchema],
    summary="Получить историю транзакций пользователя"
)
async def get_transaction_history(user_id: int, db_session: AsyncSession = Depends(get_session)):
    """
    История транзакций любого пользователя, в том числе удаленного.
    """
    # Проверяем физическое наличие пользователя в БД
    user = await UserCRUD.get_any_by_id(db_session, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Пользователь с id {user_id} никогда не существовал"
        )

    #  Получаем транзакции
    transactions = await BalanceCRUD.get_user_transactions(db_session, user_id)

    #  пометка о статусе пользователя в логах
    status = "УДАЛЕН" if user.is_deleted else "АКТИВЕН"
    logger.info(f"История транзакций для юзера {user_id} ({status}): найдено {len(transactions)} записей")

    return transactions
