from fastapi import APIRouter, HTTPException, status, Depends, Response
from app.crud.user import UserCRUD
from  database.database import get_session
from typing import Dict
import logging
from app.crud.schemas import UserRegSchema, UserAuthSchema, UserReadSchema
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from app.auth.password_hash import PasswordHash
from app.auth.access_token import set_token_cookie, delete_token_cookie
from config import get_settings
from fastapi.security import APIKeyCookie

# Указываем FastAPI, что мы используем куку с именем access_token
cookie_sec = APIKeyCookie(name="access_token", auto_error=False)

# , dependencies=[Depends(cookie_sec)]

settings = get_settings()

# Создает логгер для вывода сообщений
logger = logging.getLogger("uvicorn.error")


# Объявляем роутер, к которому привязываем маршруты
user_router = APIRouter()



@user_router.post(
   '/signup',
   response_model= Dict[str, str],
   status_code=status.HTTP_201_CREATED,
   summary="Регистрация пользователя"
)
async def signup(
        response: Response,
        user_data: UserRegSchema,
        db_session: AsyncSession=Depends(get_session)
)  -> Dict[str, str]:
    """
    **Регистрация нового пользователя по почте и паролю:**
    1. Валидация email через Pydantic.
    2. Проверка на отсутствие введеного email в БД.
    3. Пароль хэшируется.
    4. При успешной регистрции автоматически создается нулевой баланс с привязкой к пользователю.
    5. Возможна регистрация удаленного ранее пользователя со старой почтой.
    """
    # Проверка, существует ли пользователь
    existing_user = await UserCRUD.get_by_email(db_session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует"
        )
    # Создание нового пользователя

    await UserCRUD.create(db_session, user_data)
    # сохраняем токен в куки
    set_token_cookie(response, user_email=user_data.email)
    logger.info(f"Создан новый пользователь с почтой {user_data.email}")
    return   {"message": "Пользователь успешно зарегистрирован"}



@user_router.post(
    '/login',
    summary="Авторизация пользователя"
)
async def login(
        response: Response,
        user_data: UserAuthSchema,
        db_session: AsyncSession=Depends(get_session)
) -> Dict[str, str]:
    """
    Авторизация пользователя по почте и паролю. Запись токена в куки.
    """
    user = await UserCRUD.get_by_email(db_session, user_data.email)
    if user is None:
        logger.warning(f"Попытка входа: email {user_data.email} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Данная почта не зарегистрирована"
        )
    # проверка пароля
    if not PasswordHash.verify(user_data.password, user.password_hash):
        logger.warning(f"Неверный пароль для: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный пароль"
        )
   # сохраняем токен в куки
    set_token_cookie(response, user_email=user.email)
    return {"message": "Успешная авторизация"}


@user_router.post("/logout", summary="Выход из аккаунта")
async def logout(response: Response):
    """
    Выход из аккауната. Удаление токена из кук.
    """
    delete_token_cookie(response)
    return {"message": "Вы вышли из аккаунта"}


@user_router.get(
    '/get_user_by_id',
    response_model=UserReadSchema,
    summary="Получить пользователя по id"
)
async def get_user_by_id(user_id: int,  db_session: AsyncSession=Depends(get_session)):
    """
    Получить активного пользователя по id
    """
    user = await UserCRUD.get_by_id(db_session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@user_router.get(
    '/get_user_by_email',
    response_model=UserReadSchema,
    summary="Получить пользователя по emai"
)
async def get_user_by_email(email: EmailStr,  db_session: AsyncSession=Depends(get_session)):
    """
    Получить активного пользователя по emai
    """
    user = await UserCRUD.get_by_email(db_session, email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@user_router.get(
    "/get_all_users",
    response_model=list[UserReadSchema],
    summary="Получить пользователей"
)
async def get_all_users(db_session: AsyncSession = Depends(get_session)):
    """
    Получить список всех активных пользователей
    """
    try:
        return await UserCRUD.get_all(db_session)
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка пользователей"
        )


@user_router.delete(
    '/{user_id}',
    status_code=status.HTTP_200_OK,
    summary="Удаление пользователя"
)
async def delete_user(user_id: int, db_session: AsyncSession = Depends(get_session)):
    """
    **Мягкое удаление пользователя:**
    1. Проставляет флаг в БД в таблице users is_deleted=True, но фактически не удаляет.
    2. Добавляет дату в начале email для возможности повторной регистрации удаленного пользователя со старой почтой.
    """

    deleted = await UserCRUD.delete(db_session, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с id {user_id} не найден"
        )
    return {"message": f"Пользователь с id {user_id} успешно удален"}

