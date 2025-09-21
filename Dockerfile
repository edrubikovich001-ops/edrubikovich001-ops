FROM python:3.11-slim

# Ускоряем/облегчаем сборку
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Кладём всё приложение
COPY . .

# Render сам подставит PORT в переменную окружения
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
