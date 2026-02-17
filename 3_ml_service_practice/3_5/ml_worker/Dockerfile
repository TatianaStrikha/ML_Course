FROM python:3.11
WORKDIR /src
COPY ml_worker/requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
# Копируем весь корень (включая папку database и app)
COPY . .
CMD ["python", "-m", "ml_worker.main"]