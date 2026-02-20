import jwt
from config import get_settings
from fastapi import HTTPException, status, Request, Depends
from datetime import datetime, timezone, timedelta
from fastapi import Response
from app.crud.user import UserCRUD
from database.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

settings = get_settings()

def create_token(user: str) -> str:
    """
    Создает JWT токен доступа для пользователя.
    """
    # Срок действия токена
    expiration_time = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user,
        "exp": expiration_time
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """
    Проверяет валидность JWT токена.
    HTTPException: Если токен недействителен или просрочен
    """
    #  Декодируем токен. PyJWT сам проверит поле "exp",
    # если оно там есть, и выкинет ExpiredSignatureError при просрочке.
    try:
        data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return data

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истек"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )


def set_token_cookie(response: Response, user_email: str):
    """
    Сохранение токена в куки
    """
    token = create_token(user=user_email)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True, #  JS не сможет украсть токен
        samesite="lax", #  защищает от CSRF-атак
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 # Время жизни в секундах
    )


def delete_token_cookie(response: Response):
    """
    Удаляет авторизационную куку из браузера пользователя.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax"
    )


async def get_optional_user(
    request: Request,
    db_session: AsyncSession = Depends(get_session)
) -> User | None:
    """
    Тихая проверка наличия токена в куках: возвращает User, если кука верна, иначе None (без ошибок).
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = verify_token(token)
        email = payload.get("sub")
        return await UserCRUD.get_by_email(db_session, email)
    except Exception:
        return None

#
async def get_current_user(user: User = Depends(get_optional_user)) -> User:
    """
    Проверка наличия токена в куках: возвращает User, если кука верна, иначе возвращает ошибку
    """
    if not user:
        raise HTTPException(status_code=401, detail="Вы не авторизованы")
    return user