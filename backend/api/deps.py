import os
import redis
from agents_shared.kafka_client import KafkaClient
from minio import Minio

from api.services.upload_service import UploadService

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1","true","yes")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "api-group")
KAFKA_PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "docs.uploaded")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

kafka_client = KafkaClient(
    group_id=KAFKA_GROUP_ID,
    topics=[],
    client_id="api"
)

upload_service = UploadService(minio_client, MINIO_BUCKET, kafka_client, KAFKA_PRODUCE_TOPIC)

def get_upload_service():
    return upload_service
