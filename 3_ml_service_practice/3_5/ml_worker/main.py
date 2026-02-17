import uuid
import asyncio
import json
import random
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

# Генерируем короткий ID для текущего запуска
WORKER_ID = f"worker-{uuid.uuid4().hex[:4]}"

logging.basicConfig(
    level=logging.INFO, # DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(WORKER_ID)

async def process_task(message: IncomingMessage):
    """
    Логика обработки сообщения из RabbitMQ
    """

    # Контекстный менеджер 'process' подтверждает выполнение (ack) автоматически
    async with message.process():
        payload = json.loads(message.body)
        task_id = int(payload['task_id'])

        # 1. Получаем фабрику и открываем сессию вручную
        session_factory = get_session_local()

        async with session_factory() as db_session:
            try:
                logger.info(f" начинает задачу: {task_id}")

                # 2. Обновляем статус на IN_PROGRESS
                await MLTaskCRUD.update_status(db_session, task_id, TaskStatus.IN_PROGRESS)
                await db_session.commit()

                # 3. Имитация работы (2 секунды )
                await asyncio.sleep(2)

                # 4. Симуляция сбоя (10%)
                if random.random() < 0.1:
                    logger.error(f"Сбой в ML-модели для задачи {task_id}")
                    await MLTaskCRUD.refund(db_session, task_id, "Ошибка модели")
                    await db_session.commit()
                    return

                    # 5. Успех: сохраняем результат
                prediction = f"Результат "
                await MLTaskCRUD.complete_task(db_session, task_id, prediction)
                await db_session.commit()

                logger.info(f"Задача {task_id} выполнена успешно")

            except Exception as e:
                await db_session.rollback()
                logger.error(f"ERROR.Ошибка при работе с БД: {e}")
                raise e


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

    logger.info("Worker запущен. Ожидание задач...")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())


#  команда для запуска воркера :
# python -m ml_worker.main
#  команда для создания 2 воркеров в докере (по одному контейнеру на каждый):
# docker-compose up --scale ml_worker=2