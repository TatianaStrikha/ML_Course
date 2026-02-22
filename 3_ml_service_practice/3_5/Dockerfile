FROM python:3.11
WORKDIR /src
# Установка системных зависимостей для работы с БД
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Копируем всё из корня проекта в папку /code внутри контейнера
COPY . .
# Команда запуска FastAPI
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]