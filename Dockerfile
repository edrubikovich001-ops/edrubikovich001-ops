FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Запускаем веб-сервер (Render подставит порт в переменную PORT)
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
