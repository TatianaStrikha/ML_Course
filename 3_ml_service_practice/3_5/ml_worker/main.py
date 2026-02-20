# =============================================
# Логика работы ML-воркера
# =============================================
import uuid
import asyncio
import json
import re
import os
import sys
sys.path.append(os.getcwd())
from aio_pika import connect, IncomingMessage
from app.crud.ml_task import MLTaskCRUD
from app.models.enums import TaskStatus
from database.database import get_session_local
import logging
from config import get_settings
# необходим импорт моделей, чтобы SQLAlchemy знал о связях (Relationship)
from app.models.user import User
from app.models.balance import Balance
from app.models.ml_task import MLTask
from app.models.ml_model import MLModel
from app.models.transaction import Transaction
import pymorphy3 # библиотека, которая выполняет роль ML-модели
from ml_worker.dictionary import RUS_LABELS, ATTRIBUTES_ORDER
import random


# Инициализируем библиотеку один раз при старте воркера
morph = pymorphy3.MorphAnalyzer()


# Генерируем короткий ID для текущего запуска
WORKER_ID = f"worker-{uuid.uuid4().hex[:4]}"

logging.basicConfig(
    level=logging.INFO, # DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(WORKER_ID)


async def process_task(message: IncomingMessage):
    """Логика работы воркера"""
    async with message.process():
        payload = json.loads(message.body)
        task_id = int(payload['task_id'])
        user_text = payload['features'].get('input', '')

        async with get_session_local()() as db_session:
            try:
                logger.info(f"Воркер начал работу над задачей №{task_id}")
                logger.info(f"Текст для разбора: {user_text}")

                # 1. Меняем статус на InProgress
                await MLTaskCRUD.update_status(db_session, task_id, TaskStatus.IN_PROGRESS)
                await db_session.commit()

                #  имитация сбоя для тестирования работы функции refund
                # if random.random() < 0.5:
                #     logger.warning(f"Имитация сбоя для задачи {task_id}...")
                #     trigger_error = 1 / 0

                    # 2. Работа ML-модели: морфологический разбор
                # Разбиваем текст на слова и очищаем от знаков препинания
                words = [w.strip('.,!?-()":;').lower() for w in user_text.split()]
                # задаем порядок вывода характеристик

                analysis_results = []
                for word in words:
                    if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', word):
                        continue
                    parses = morph.parse(word)
                    if parses:
                        p = parses[0]
                        full_info = []

                        for attr_name in ATTRIBUTES_ORDER:
                            attr_value = getattr(p.tag, attr_name, None)
                            if attr_value:
                                # Ищем перевод в словаре, если нет - оставляем код
                                label = RUS_LABELS.get(str(attr_value), str(attr_value))
                                full_info.append(label)

                        # Собираем результат для одного слова
                        description = ", ".join(full_info)
                        analysis_results.append(f"{p.word} ({description})")

                # 3. Формируем финальную строку результата
                prediction = " | ".join(analysis_results)

                # результат работы
                final_output = prediction

                # 4. Сохраняем в БД статус Completed
                await MLTaskCRUD.complete_task(db_session, task_id, final_output)
                await db_session.commit()

                logger.info(f"Задача № {task_id} успешно завершена")

            except Exception as e:
                await db_session.rollback()
                logger.error(f" Критическая ошибка задачи {task_id}: {e}")
                # Возвращаем деньги и меняем статус на FAILED
                # Внутри refund создаст транзакцию REFUND и прибавит деньги к балансу
                await MLTaskCRUD.refund(db_session, task_id, reason=str(e))
                await db_session.commit()
                # Не «поднимаем» ошибку выше (raise), чтобы RabbitMQ не пытался бесконечно переповторять эту задачу


async def main():
    settings = get_settings()
    logger.info("Подключение к RabbitMQ...")
    connection = await connect(settings.RABBITMQ_URL)
    channel = await connection.channel()

    # 1 задача за раз
    await channel.set_qos(prefetch_count=1)

    # Объявляем очередь (durable=True, чтобы не пропала при перезагрузке)
    queue = await channel.declare_queue("ml_tasks", durable=True)

    #  no_ack=False - возврат задачи в очередь, если воркер упадет
    await queue.consume(process_task, no_ack=False)

    logger.info("Воркер запущен. Ожидание задач...")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())


#  команда для запуска воркера :
# python -m ml_worker.main
#  команда для создания 2 воркеров в докере (по одному контейнеру на каждый):
# docker-compose up --scale ml_worker=2