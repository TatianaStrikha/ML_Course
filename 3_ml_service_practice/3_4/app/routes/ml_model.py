from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from app.crud.ml_model import MLModelCRUD
from app.schemas import MLModelReadSchema, MLModelCreateSchema
import logging


logger = logging.getLogger("uvicorn.error")

ml_model_router = APIRouter()

@ml_model_router.post("/", response_model=MLModelReadSchema, summary="Добавить новую ML-модель")
async def create_model(model_data: MLModelCreateSchema, db_session: AsyncSession = Depends(get_session)):
    """Добавляет модель в базу. Укажите название и цену за один запрос."""
    return await MLModelCRUD.create(db_session, model_data)

@ml_model_router.get(
    '/get',
    response_model=MLModelReadSchema,
    summary="Получить  ML-модель по id"
)
async def get(model_id: int,  db_session: AsyncSession=Depends(get_session)):
    model = await MLModelCRUD.get(db_session, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="ML-модель не найдена")
    return model

@ml_model_router.get("/get_all", response_model=list[MLModelReadSchema], summary="Список всех доступных моделей")
async def get_all(db_session: AsyncSession = Depends(get_session)):
    """Возвращает список моделей с их ценами."""
    try:
        return await MLModelCRUD.get_all(db_session)
    except Exception as e:
        logger.error(f"Ошибка при получении списка ML-моделей: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка ML-моделей"
        )



