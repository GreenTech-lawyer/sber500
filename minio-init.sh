#!/bin/sh
# Ждём, пока MinIO станет доступен
until curl -s http://127.0.0.1:9000/minio/health/live; do
  echo "Waiting for MinIO..."
  sleep 2
done

# Настраиваем alias для mc
mc alias set local http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Создаём бакет, если не существует
mc mb --ignore-existing local/documents
