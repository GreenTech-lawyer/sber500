import uuid
from datetime import timedelta

from minio import Minio
from agents_shared.kafka_client import KafkaClient

class UploadService:
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
            expires=timedelta(seconds=expires)
        )
        return {"upload_url": url, "object_id": object_id, "bucket": self.bucket}

    def notify_upload(self, object_id: str, bucket: str, user_id: str, file_id: str | None = None, content_type: str | None = None):
        """
        Публикация события об успешной загрузке файла в Kafka.
        """
        file_id = file_id or object_id
        payload = {
            "bucket": bucket,
            "object_id": object_id,
            "user_id": user_id,
            "file_id": file_id,
            "content_type": content_type
        }
        self.kafka.produce(self.kafka_topic, payload, key=file_id)
        return {"status": "ok", "file_id": file_id}
