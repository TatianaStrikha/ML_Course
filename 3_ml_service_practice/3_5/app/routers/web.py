from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from app.auth.password_hash import PasswordHash
from app.auth.access_token import get_current_user, get_optional_user, set_token_cookie, delete_token_cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.database import get_session
from app.crud.user import UserCRUD
from app.crud.balance import BalanceCRUD
from app.crud.ml_task import MLTaskCRUD
from app.crud.ml_model import MLModelCRUD
from app.crud.schemas import MLTaskReadSchema, MLTaskCreateSchema
from app.routers.ml_task import send_to_rabbit
from app.crud.schemas import UserRegSchema
from app.models.enums import TaskStatus
import logging
import json
from datetime import datetime
from aio_pika import connect, Message
from config import get_settings
from app.models.user import User
from decimal import Decimal
from fastapi.security import APIKeyCookie




web_router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@web_router.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request):
    """Главная страница (доступна всем)"""
    return templates.TemplateResponse("home.html", {"request": request})


@web_router.get("/signup", response_class=HTMLResponse)
async def signup_page(
        request: Request,
        user: User = Depends(get_optional_user)  # Проверяем "тихо"
):
    """Страница регистрации"""
    # Если пользователь уже авторизован переадресовываем в профиль
    if user:
        return RedirectResponse(url="/profile", status_code=302)
    # иначе -страницу регистрации
    return templates.TemplateResponse("signup.html", {"request": request})



@web_router.post("/signup")
async def signup_handler(
        request: Request,
        user_name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        db_session: AsyncSession = Depends(get_session)
):
    """Логика регистрации"""
    try:
        # 1. Валидация данных через существующую схему
        user_data = UserRegSchema(
            user_name=user_name,
            email=email,
            password=password
        )

        # 2. Проверка, не занят ли email
        existing_user = await UserCRUD.get_by_email(db_session, user_data.email)
        if existing_user:
            raise ValueError("Пользователь с таким email уже существует")

        # 3. Создание пользователя (и баланса внутри CRUD)
        new_user = await UserCRUD.create(db_session, user_data)

        # 4. Автоматический вход: создаем редирект и ставим куку
        redirect = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
        set_token_cookie(redirect, user_email=new_user.email)

        return redirect

    except (ValueError, ValidationError) as e:
        # Если ошибка (валидации или логики) — возвращаем форму с текстом ошибки
        error_msg = e.errors()[0]['msg'] if hasattr(e, 'errors') else str(e)
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": error_msg
        })


@web_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User = Depends(get_optional_user) # Проверяем "тихо"
):
    """Страница авторизации"""
    # Если пользователь уже авторизован переадресовываем в профиль
    if user:
        return RedirectResponse(url="/profile", status_code=302)

    # Если нет - показываем форму входа
    return templates.TemplateResponse("login.html", {"request": request})


@web_router.post("/login")
async def login_handler(
        request: Request,
        username: str = Form(...),  # Имя поля в HTML 'name="username"'
        password: str = Form(...),
        db_session: AsyncSession = Depends(get_session)
):
    """Логика авторизации"""
    # 1. Проверяем пользователя
    user = await UserCRUD.get_by_email(db_session, username)

    if not user or not PasswordHash.verify(password, user.password_hash):
        # Если ошибка — возвращаем ту же страницу, но с текстом ошибки
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль"}
        )

    # 2. Если всё ок — создаем редирект в личный кабинет
    redirect = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)

    # 3. Устанавливаем куку в этот редирект
    set_token_cookie(redirect, user_email=user.email)

    return redirect



@web_router.get("/profile", response_class=HTMLResponse)
async def get_profile_page(
    request: Request,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session)
):
    """Главная страница профиля"""
    # Получаем первую модель, чтобы узнать её стоимость
    active_model = await MLModelCRUD.get_first_model(db_session)

    # получаем баланс из бД
    user_balance = await BalanceCRUD.get_any(db_session, user.user_id)

    #   получаем 5 последних задач
    history = await MLTaskCRUD.get_history(db_session, user_id=user.user_id, limit=5)

    #  Отправляем в шаблон чистый объект баланса отдельно
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "balance": user_balance,
        "history": history,
        "ml_model": active_model
    })


@web_router.get("/profile/top_up", response_class=HTMLResponse)
async def top_up_page(
        request: Request,
        user: User = Depends(get_current_user),
        db_session: AsyncSession = Depends(get_session)  # Добавь сессию
):
    """ Отображение старинцы пополнения баланса"""
    # Получаем объект баланса из БД
    user_balance = await BalanceCRUD.get_any(db_session, user.user_id)

    return templates.TemplateResponse("top_up.html", {
        "request": request,
        "user": user,
        "balance": user_balance
    })


@web_router.post("/profile/top_up")
async def do_top_up(
        request: Request,
        amount: float = Form(...),  # Получаем сумму из HTML-формы
        user: User = Depends(get_current_user),
        db_session: AsyncSession = Depends(get_session)
):
    """Логика пополнения баланса"""
    try:
        # Превращаем float в Decimal для точности денег
        top_up_decimal = Decimal(str(amount))

        await BalanceCRUD.top_up(db_session, user.user_id, top_up_decimal)

        # После успеха возвращаемся в профиль
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)

    except ValueError as e:
        # Если юзер удален или ошибка — возвращаем форму с текстом ошибки
        return templates.TemplateResponse("top_up.html", {
            "request": request, "user": user, "error": str(e)
        })

@web_router.get("/profile/transactions", response_class=HTMLResponse)
async def get_transactions_page(
    request: Request,
    user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session)
):
    """История транзакций"""
    transactions = await BalanceCRUD.get_user_transactions(db_session, user_id=user.user_id)

    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "user": user,
        "transactions": transactions
    })


@web_router.get("/profile/history", response_class=HTMLResponse)
async def get_history_page(
        request: Request,
        user: User = Depends(get_current_user),
        db_session: AsyncSession = Depends(get_session)
):
    """История запросов"""
    history = await MLTaskCRUD.get_history(db_session, user_id=user.user_id)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "user": user,
        "history": history
    })

demo_model=1

@web_router.post("/profile/predict")
async def web_predict_handler(
        request: Request,
        input_text: str = Form(...),
        user: User = Depends(get_current_user),
        db_session: AsyncSession = Depends(get_session)
):
    """Отправка запроса в воркер"""
    try:
        #  получаем актуальную модель из БД
        active_model = await MLModelCRUD.get_first_model(db_session)
        # Если текст плохой — Pydantic сам выкинет ошибку, которую мы поймаем ниже
        validated_data = MLTaskCreateSchema(input_data=input_text)

        # Вызываем метод создания задачи
        # Он сам проверит баланс, спишет деньги и создаст транзакцию SPEND
        task = await MLTaskCRUD.create(
            db_session,
            user_id=user.user_id,
            model_id=active_model.model_id,
            input_data=validated_data.input_data
        )

        # Отправка в очередь
        await send_to_rabbit(task.task_id, validated_data.input_data, active_model.model_id)

        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)

    except (ValueError, ValidationError) as e:
        # Сюда попадут ошибки: "Недостаточно средств", "Модель не найдена"
        # или "Текст должен содержать буквы" из валидатора
        #  Снова получаем данные для страницы
        history = await MLTaskCRUD.get_history(db_session, user_id=user.user_id, limit=5)
        # Получаем баланс,и мл-модель так как шаблон profile.html требует эти данные
        user_balance = await BalanceCRUD.get_any(db_session, user.user_id)
        active_model = await MLModelCRUD.get_first_model(db_session)

        # Формируем текст ошибки
        if hasattr(e, 'errors'):
            # Ошибка от Pydantic (ValidationError)
            error_msg = e.errors()[0]['msg']
        else:
            # Ошибка ValueError (например, от базы про баланс)
            error_msg = str(e)

        return templates.TemplateResponse("profile.html", {
            "request": request,
            "user": user,
            "balance": user_balance,
            "history": history,
            "ml_model": active_model,
            "error": error_msg  # Выводим пользователю понятную причину
        })


@web_router.post("/logout")
async def logout_handler():
    """
    Выход из системы: удаление куки и редирект на главную.
    """
    # Создаем редирект на главную страницу
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    # Удаляем токен из кук
    delete_token_cookie(response)
    return response
