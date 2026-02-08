import time
import sys
import os
import datetime
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.database import init_db
from user import User
from ml_model import MLModel
from enums import UserRole, TaskStatus, TransactionType
from ml_task import MLTask
from transaction import Transaction
from balance import Balance


if __name__ == "__main__":
    print("Запуск приложения...")
    try:
        # Начальная инициализации БД
        print("Инициализация базы данных...")
        engine = init_db(drop_all=True)
        print("База данных готова!")

        # содание (регистрация) демо-пользователя и запись в таблицу БД
        Session = sessionmaker(bind=engine)
        session = Session()
        demo_user = User(user_name="demo",
                                     email="demo@mail.ru",
                                     password_hash="demo",
                                     role=UserRole.USER,
                                     registration_date =datetime.datetime.now())

        # список моделей
        demo_model =MLModel(model_name = 'LLM',
                                               cost_per_prediction = Decimal('100.00'),
                                              description = 'Large Language Model')

        session.add(demo_user)
        session.add(demo_model)
        session.commit()

        # авторизация пользователя - поиск пользователя по имени (почте)
        user = session.query(User).filter_by(user_name="demo").first()
        print(f"Результат выполнения запроса: {user.user_id}, {user.user_name}")


        # инициализация баланса
        demo_user_balance = Balance(
            user_id=demo_user.user_id,
            amount=Decimal('0.00')
        )
        session.add(demo_user_balance)
        session.commit()

        # пополнеие баланса
        demo_user_balance.amount += 200
        transaction = Transaction.top_up_balance(user=demo_user, amount=200)
        session.add(transaction)
        session.commit()

        # ошибка при указании отрицаиельной сумма
        #transaction = Transaction.top_up_balance(user=demo_user, amount=-70)
        #session.add(transaction)
        #session.commit()

        #  получить модель для работы
        model = session.query(MLModel).first()

        if (demo_user_balance.amount <= model.cost_per_prediction):
            raise Exception (f"Не достаточно средств: на балансе {demo_user_balance.amount}, стоимость операции {model.cost_per_prediction}")


        # отправить в модель данные для предсказания
        task  = MLTask(
            user_id = demo_user.user_id,
            model_id = model.model_id,
            input_data = "данные",  # данные для предсказания
            status = TaskStatus.WAITING,
            prediction_result = None
        )
        result = task.execute(user=demo_user)
        if (result):
            print(f"Получено предсказание: {task.prediction_result}")  #{task.get_result()}")
        session.add(task)
        session.commit()


        # списание c баланса денег за предсказание
        demo_user_balance.amount -= 70
        transaction = Transaction.top_up_balance(user=demo_user, amount=70)
        session.add(transaction)
        session.commit()

    except Exception as exc:
        print(f"Критическая ошибка: {exc}")
        sys.exit(1)

    print("Приложение запущено успешно!")
    while True:
        print("Работаем...")
        time.sleep(10)