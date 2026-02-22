FROM python:3.11
WORKDIR /app
# Установка зависимостей
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
#  Копируем зависимости именно воркера (путь от корня проекта)
COPY ml_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Установка словарей для морфологического анализа (обязательно для pymorphy3)
RUN pip install pymorphy3-dicts-ru
# Копируем общий конфиг из корня проекта
COPY config.py .
# Копируем всё содержимое папки воркера в подпапку ml_worker
COPY ml_worker/ ./ml_worker/
#. Настройка переменной окружения, чтобы Python видел файлы в /app
# Это позволит делать "from config import settings"
ENV PYTHONPATH=/app
#  Запуск воркера
CMD ["python", "ml_worker/main.py"]