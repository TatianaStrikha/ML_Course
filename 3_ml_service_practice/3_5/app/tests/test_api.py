# =============================================
# Тест api эндпоинтов
# =============================================
# app/tests/test_api.py - запуск
import pytest
from app.crud.ml_task import MLTaskCRUD


demo_user = {
    "email": "test@mail.ru",
    "password":"password123"
}


@pytest.mark.asyncio
async def test_signup_fail(client):
    """1. Регистрация с невалидными данными"""
    # Короткий пароль
    resp = await client.post("/users/signup", json={"user_name": "User","email": "a@test.ru", "password": "123"})
    assert resp.status_code == 422  # Pydantic вернет 422 для JSON
    # # Некорректный email
    resp = await client.post("/users/signup", json={"user_name": "User","email": "atest.ru", "password": "123456"})
    assert resp.status_code == 422  # Pydantic вернет 422 для JSON


@pytest.mark.asyncio
async def test_signup(client):
    """2. Регистрация пользователя """
    resp = await client.post("/users/signup", json={"user_name": "User","email": "test@mail.ru", "password": "password123"})
    assert resp.status_code == 201
    assert resp.json()["message"] == "Пользователь успешно зарегистрирован"
    assert "access_token" in client.cookies


@pytest.mark.asyncio
async def test_balance(client):
    """3. Тест баланса и пополнения"""
     # Получение баланса
    resp = await client.get("/balance/1")
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == 0.0

    # Пополнение
    resp = await client.post("/balance/top_up/1", json={"amount": 100.0})
    assert resp.status_code == 200
    assert float(resp.json()["amount"] )== 100.0


@pytest.mark.asyncio
async def test_ml_tasks_fail(client):
    """4. Тест ML-запроса с невалидными данными"""
    # авторизация
    await client.post("/users/login", json=demo_user)

    # Отправка цифр вместо текста
    resp = await client.post("/ml_task/predict", json={"input_data": "12345"})
    assert resp.status_code == 422
    assert "input_data" in resp.text  # Ошибка валидации поля


@pytest.mark.asyncio
async def test_ml_tasks(client):
    """5. Тест успешного ML-запроса и истории"""
    # авторизация
    await client.post("/users/login", json=demo_user)

    # Запрос
    resp = await client.post("/ml_task/predict", json={"input_data": "Успешный тест"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "Waiting"

    # на балансе должно быть 0
    resp = await client.get("/balance/1")
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == 0.0

    # История транзакций
    resp_tx = await client.get("/balance/transactions/1")
    # Проверяем наличие сумм в JSON-ответе
    amounts = [float(tx["amount"]) for tx in resp_tx.json()]
    assert 100.0 in amounts
    assert -100.000 in amounts


@pytest.mark.asyncio
async def test_low_balance_error(client):
    """6. Тест недостаточности баланса"""
    # авторизация
    await client.post("/users/login", json=demo_user)

    resp = await client.post("/ml_task/predict", json={"input_data": "Денег нет"})
    assert resp.status_code == 400
    assert "Недостаточно средств" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_refund(client, db_session):
    """7. Тест возврата средств"""
    # авторизация
    await client.post("/users/login", json=demo_user)

    # пополняем баланс
    await client.post("/balance/top_up/1", json={"amount": 100.0})

    # Делаем запрос
    await client.post("/ml_task/predict", json={"input_data": "Тестовый запрос"})

    # Имитируем Refund в БД
    history = await MLTaskCRUD.get_history(db_session, user_id=1, limit=1)
    if history:
        # Прямо вызываем refund в тестовой базе
        await MLTaskCRUD.refund(db_session, history[0].task_id, reason="Error")
        await db_session.commit()

    # Проверяем возврат
    resp = await client.get("/balance/1")
    assert float(resp.json()["amount"]) == 100.0


