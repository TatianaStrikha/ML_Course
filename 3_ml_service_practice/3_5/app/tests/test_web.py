# =============================================
# Тест web эндпоинтов
# =============================================
# pytest app/tests/test_web.py - запуск
import pytest
from app.crud.ml_task import MLTaskCRUD


demo_user = {
    "username": "test@mail.ru",
    "password":"password123"
}

@pytest.mark.asyncio
async def test_signup_fail(client):
    """1. Регистрация пользователя с невалидными данными."""

    # Короткий пароль
    bad_pass = {"user_name": "User", "email": "test@mail.ru", "password": "123"}
    res = await client.post("/signup", data=bad_pass)
    assert res.status_code == 200 # Остаемся на странице регистрации
    assert "password" in res.text.lower() # Проверяем, что в тексте есть упоминание ошибки пароля

    # Некорректный email
    bad_email = {"user_name": "User", "email": "not-an-email", "password": "password123"}
    res = await client.post("/signup", data=bad_email)
    assert "email" in res.text.lower() # Проверяем, что в тексте есть упоминание ошибки email


@pytest.mark.asyncio
async def test_signup(client):
    """2. Регистрация пользователя"""
    # Регистрация (возвращает 303 Redirect в профиль)
    demo_user_data = {
        "user_name": "test_name",
        "email": "test@mail.ru",
        "password": "password123"
    }
    reg_response = await client.post("/signup", data=demo_user_data)
    assert reg_response.status_code == 303
    assert "access_token" in client.cookies

@pytest.mark.asyncio
async def test_balance(client):
    """3.Тест баланса"""

    # удаляем куки от предыдущих тестов и повторно авторизуемся  для чистоты теста
    await client.post("/logout")
    await client.post("/login", data=demo_user)

    # Проверка начального нулевого баланса (в HTML коде профиля)
    profile_view = await client.get("/profile")
    assert  "0.0" in profile_view.text

    # Пополнение баланса
    top_up_res = await client.post("/profile/top_up", data={"amount": "100.00"})
    assert top_up_res.status_code == 303

    # Проверка обновленного баланса
    profile_after_topup = await client.get("/profile")
    assert "100.0" in profile_after_topup.text

@pytest.mark.asyncio
async def test_ml_tasks_fail(client):
    """4. Тест отправки ML-запросов с невалидными данными"""

    await client.post("/logout")
    await client.post("/login", data=demo_user)

    # Отправка некорректных данных (только цифры - сработает валидатор схемы)
    bad_ml_data = {"input_text": "12345678"}
    bad_res = await client.post("/profile/predict", data=bad_ml_data)
    # Вместо редиректа вернется страница с ошибкой (код 200)
    assert bad_res.status_code == 200
    assert "Текст должен содержать буквы" in bad_res.text

    # Проверка того, что деньги не списаны
    profile_after_ml = await client.get("/profile")
    assert "100.0" in profile_after_ml.text


@pytest.mark.asyncio
async def test_ml_tasks(client):
    """5. Тест отправки ML-запросов"""

    await client.post("/logout")
    await client.post("/login", data=demo_user)

    # Отправка корректных данных
    ml_data = {"input_text": "Привет, это тестовое предложение"}
    ml_res = await client.post("/profile/predict", data=ml_data)
    assert ml_res.status_code == 303

    # Проверка списания
    profile_after_ml = await client.get("/profile")
    assert "0.0" in profile_after_ml.text

    # История транзакций
    tx_history = await client.get("/profile/transactions")
    assert "100.0" in tx_history.text  # Сумма пополнения
    assert "-100.0" in tx_history.text  # Сумма списания

    # История ML-запросов
    ml_history = await client.get("/profile/history")
    assert "Привет, это тестовое предложение" in ml_history.text


@pytest.mark.asyncio
async def test_low_balance_error(client):
    """6. Тест недостаточности баланса"""

    await client.post("/logout")
    await client.post("/login", data=demo_user)

    # пытаемся запустить анализ. проверяем, что вывело ошибку
    res = await client.post("/profile/predict", data={"input_text": "Нет денег"})
    assert "Недостаточно средств" in res.text


@pytest.mark.asyncio
async def test_refund(client, db_session):
    """7. Тест возврата средств при сбое"""

    await client.post("/logout")
    await client.post("/login", data=demo_user)

    # пополняем баланс
    await client.post("/profile/top_up", data={"amount": "100.00"})

    # создаем задачу, списываем 100
    await client.post("/profile/predict", data={"input_text": "Текст для сбоя"})

    #  Имитируем вызов refund (как это сделал бы воркер при ошибке)
    history = await MLTaskCRUD.get_history(db_session, user_id=1, limit=1)
    if history:
        # Прямо вызываем refund в тестовой базе
        await MLTaskCRUD.refund(db_session, history[0].task_id, reason="Error")
        await db_session.commit()

    # проверяем, что деньги вернулись (снова 100.0)
    res = await client.get("/profile")
    assert "100.0" in res.text

    # проверяем, что в транзакциях появился Refund
    res_tx = await client.get("/profile/transactions")
    assert "Возврат" in res_tx.text or "REFUND" in res_tx.text
