# =============================================
# Класс Модель Машинного Обучения
# =============================================
from database.database import Base
from sqlalchemy import Column, Integer, String, Numeric
from decimal import Decimal

class MLModel(Base):
    __tablename__='models'
    model_id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String)
    cost_per_prediction = Column(Numeric(precision=15, scale=2), default=Decimal('0.00')) # цена за одно предсказание
    description = Column(String)
