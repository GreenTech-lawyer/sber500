import uuid
from datetime import timedelta

from fastapi import Depends
from minio import Minio
from agents_shared.kafka_client import KafkaClient
from redis import Redis

from api.deps import get_redis_client
from agents_shared.redis_storage import get_active_documents_for_session, add_active_document

MINIO_PUBLIC_URL = "http://localhost/minio-api"

class FilesService:
    def __init__(
        self,
        minio_client: Minio,
        bucket: str,
        kafka_client: KafkaClient,
        kafka_topic: str,
    ):
        self.minio = minio_client
        self.bucket = bucket
        self.kafka = kafka_client
        self.kafka_topic = kafka_topic

    def create_presigned_url(self, filename: str, expires: int = 3600):
        """
        Генерация pre-signed URL для загрузки файла в MinIO.
        """
        object_id = f"{uuid.uuid4().hex}_{filename}"
        url = self.minio.presigned_put_object(
            bucket_name=self.bucket,
            object_name=object_id,
            expires=timedelta(seconds=expires),
        )
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        public_url = urlunparse(parsed._replace(scheme="http", netloc="localhost", path="/minio-api" + parsed.path))

        return {"upload_url": public_url, "object_id": object_id, "bucket": self.bucket}

    def notify_upload(self, object_id: str, bucket: str, user_id: str, file_id: str | None = None, content_type: str | None = None, session_id: str | None = None, redis_client: Redis = Depends(get_redis_client)):
        """
        Публикация события об успешной загрузке файла в Kafka.
        Также, если передан session_id, сразу добавляем файл в активные документы сессии в Redis,
        чтобы фронт мог получить обновлённый список без ожидания потребителя Kafka.
        """
        file_id = file_id or object_id
        payload = {
            "bucket": bucket,
            "object_id": object_id,
            "user_id": user_id,
            "file_id": file_id,
            "content_type": content_type
        }

        # try to add to redis active docs set synchronously if session_id provided
        try:
            if session_id and redis_client:
                add_active_document(redis_client, session_id, file_id)
        except Exception:
            # non-fatal: log in production, but don't fail notify
            pass

        # still produce event for downstream processing
        try:
            self.kafka.produce(self.kafka_topic, payload, key=file_id)
        except Exception:
            # non-fatal
            pass

        return {"status": "ok", "file_id": file_id}

    def get_files_for_session(self, session_id: str, redis_client: Redis):
        """
        Получение списка файлов, связанных с сессией.
        """
        return get_active_documents_for_session(redis_client, session_id)
