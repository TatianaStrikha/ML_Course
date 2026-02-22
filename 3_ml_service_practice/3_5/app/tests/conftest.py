import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock
from app.api import app
from app.models.registry import metadata
from app.database import get_session
from app.models.ml_model import MLModel

# тестовая БД
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # сохраняет одну БД на все соединения в тесте
)

TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture
async def db_session():
    """
    Фикстура для прямого доступа к тестовой БД в коде теста.
    Использует тот же TestingSessionLocal, что и остальной проект.
    """
    async with TestingSessionLocal() as session:
        yield session

# Фикстура для инициализации таблиц перед тестами
@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    #  создаем тестовую модель
    async with TestingSessionLocal() as session:
        default_model = MLModel(
            model_id=1,
            model_name="Test Model",
            cost_per_prediction=100.0,
            description="Model for tests"
        )
        session.add(default_model)
        await session.commit()

    yield
    # Очистка после всех тестов
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


#  Подмена  зависимости get_session в FastAPI
@pytest.fixture(autouse=True)
async def override_get_session():
    async def _get_test_session():
        async with TestingSessionLocal() as session:
            yield session

    # Заменяем реальную сессию на тестовую во всех роутерах
    app.dependency_overrides[get_session] = _get_test_session
    yield
    # Очищаем подмену после завершения теста
    app.dependency_overrides.clear()


#  Заглушка для RabbitMQ
@pytest.fixture(autouse=True)
def mock_rabbit(mocker):
    return mocker.patch("app.routers.ml_task.send_to_rabbit", new_callable=AsyncMock)

#  Заглушка для RabbitMQ web
@pytest.fixture(autouse=True)
def mock_rabbit_web(mocker):
    return mocker.patch("app.routers.web.send_to_rabbit", new_callable=AsyncMock)


#  Асинхронный клиент для выполнения HTTP-запросов
@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

