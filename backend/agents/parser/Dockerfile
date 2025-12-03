FROM python:3.13-slim AS builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential \
    libtiff5-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY agents/parser/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/libs/agents_shared/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-rus poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

RUN groupadd -r app && useradd -r -g app app && chown -R app:app /app
USER app

CMD ["python", "-m", "agents.parser.src.main"]
