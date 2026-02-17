# =============================================
# Функции с Ml моделями для использования в эндпоинтах
# =============================================
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ml_model import MLModel
from app.schemas import MLModelCreateSchema

class MLModelCRUD:
    @staticmethod
    async def create(db_session: AsyncSession, model_data: MLModelCreateSchema) -> MLModel:
        """
        Создание ML модели в БД
        """
        new_model = MLModel(
            model_name=model_data.model_name,
            cost_per_prediction=model_data.cost_per_prediction,
            description=model_data.description
        )
        db_session.add(new_model)
        await db_session.commit()
        await db_session.refresh(new_model)
        return new_model

    @staticmethod
    async def get(db_session: AsyncSession, model_id: int) -> MLModel | None:
        """
        Получение модели по id
        """
        result = await db_session.execute(select(MLModel).where(MLModel.model_id == model_id))
        return result.scalar_one_or_none()


    @staticmethod
    async def get_all(db_session: AsyncSession):
        """
        Получение списка всех ML моделей из БД
        """
        result = await db_session.execute(select(MLModel))
        return result.scalars().all()

