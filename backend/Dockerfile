FROM python:3.13-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/libs/agents_shared/src

RUN apt-get update && \
    apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host ${SERVER_HOST:-0.0.0.0} --port ${SERVER_PORT:-8000}"]
