import os
import logging
import signal
from typing import Optional, Dict, Any

from minio import Minio
import time

from agents_shared.kafka_client import KafkaClient

from .ocr_engine import ocr_from_pdf_bytes, ocr_from_image_bytes
from .storage import save_text

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "parser-group")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "docs.uploaded").split(",")
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "docs.parsed")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("parser")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

kafka_client = KafkaClient(
    group_id=KAFKA_GROUP_ID,
    topics=CONSUME_TOPICS,
    client_id="parser"
)

_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, stopping", signum)
    _should_stop = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def fetch_object_bytes(bucket: str, object_id: str, max_retries: int = 3) -> Optional[bytes]:
    for attempt in range(1, max_retries + 1):
        try:
            obj = minio_client.get_object(bucket, object_id)
            data = obj.read()
            obj.close()
            obj.release_conn()
            return data
        except Exception as e:
            logger.warning("MinIO get_object attempt %d failed: %s", attempt, e)
            time.sleep(0.5 * attempt)
    logger.error("Failed to fetch object %s from bucket %s after %d attempts", object_id, bucket, max_retries)
    return None


def handle_upload_event(topic: str, msg: Dict[str, Any], key: Optional[str]):
    """
    Обработчик сообщений Kafka.
    topic: реальный топик, с которого пришло сообщение
    msg: декодированный словарь с данными
    key: ключ Kafka-сообщения
    """
    logger.info("Received upload event from topic %s: key=%s msg=%s", topic, key, msg)
    bucket = msg.get("bucket")
    object_id = msg.get("object_id")
    file_id = msg.get("file_id") or object_id or "unknown"

    if not bucket or not object_id:
        logger.error("Invalid message: missing bucket/object_id: %s", msg)
        return

    data = fetch_object_bytes(bucket, object_id)
    if data is None:
        kafka_client.produce("docs.upload.failed", {
            "user_id": msg.get("user_id"),
            "file_id": file_id,
            "bucket": bucket,
            "object_id": object_id
        }, key=key or file_id)
        return

    try:
        if data[:4] == b"%PDF":
            logger.info("Detected PDF for file_id=%s, running ocr_from_pdf_bytes", file_id)
            text = ocr_from_pdf_bytes(data)
        else:
            logger.info("Assuming image for file_id=%s, running ocr_from_image_bytes", file_id)
            text = ocr_from_image_bytes(data)
    except Exception:
        logger.exception("OCR failed for file %s, trying image fallback", file_id)
        try:
            text = ocr_from_image_bytes(data)
        except Exception:
            logger.exception("OCR completely failed for file %s", file_id)
            kafka_client.produce("docs.parse.failed", {
                "user_id": msg.get("user_id"),
                "file_id": file_id
            }, key=key or file_id)
            return

    try:
        redis_key = save_text(file_id, text)
    except Exception:
        logger.exception("Failed to save parsed text for file %s", file_id)
        short = (text or "")[:4000]
        kafka_client.produce(PRODUCE_TOPIC, {
            "user_id": msg.get("user_id"),
            "file_id": file_id,
            "analysis_text": short
        }, key=key or file_id)
        return

    kafka_client.produce(PRODUCE_TOPIC, {
        "user_id": msg.get("user_id"),
        "file_id": file_id,
        "redis_key": redis_key
    }, key=key or file_id)
    logger.info("Parsed file %s, saved to %s and published to %s", file_id, redis_key, PRODUCE_TOPIC)


def main_loop():
    logger.info("Parser agent started. Listening topics: %s", CONSUME_TOPICS)

    kafka_client.on_message = handle_upload_event

    try:
        kafka_client.listen_forever(poll_timeout=1.0)
    except KeyboardInterrupt:
        logger.info("Parser interrupted by user")
    except Exception as e:
        logger.exception("Unexpected parser main loop error: %s", e)
    finally:
        logger.info("Parser agent stopped.")


if __name__ == "__main__":
    main_loop()
