import logging
import time
from typing import Optional, Dict, Any
from minio import Minio

from .ocr_engine import ocr_from_pdf_bytes, ocr_from_image_bytes
from .storage import save_text_for_session, add_active_document_local, get_active_documents_for_session_local

logger = logging.getLogger("parser.service")


class ParserService:
    def __init__(self, minio_client: Minio, kafka_producer):
        self.minio = minio_client
        self.kafka = kafka_producer

    def fetch_object_bytes(self, bucket: str, object_id: str, max_retries: int = 3) -> Optional[bytes]:
        for attempt in range(1, max_retries + 1):
            try:
                obj = self.minio.get_object(bucket, object_id)
                data = obj.read()
                obj.close()
                obj.release_conn()
                return data
            except Exception as e:
                logger.warning("MinIO get_object attempt %d failed: %s", attempt, e)
                time.sleep(0.5 * attempt)
        logger.error("Failed to fetch object %s from bucket %s after %d attempts", object_id, bucket, max_retries)
        return None

    def process_upload_event(self, topic: str, msg: Dict[str, Any], key: Optional[str]):
        logger.info("Received upload event from topic %s: key=%s msg=%s", topic, key, msg)
        bucket = msg.get("bucket")
        object_id = msg.get("object_id")
        file_id = msg.get("file_id") or object_id or "unknown"
        session = msg.get("session_id")

        if file_id in get_active_documents_for_session_local(session_id=session):
            logger.info("File %s already processed for session %s, skipping", file_id, session)
            return

        if not bucket or not object_id:
            logger.error("Invalid message: missing bucket/object_id: %s", msg)
            return

        data = self.fetch_object_bytes(bucket, object_id)
        if data is None:
            self.kafka.produce("docs.upload.failed", {
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
                self.kafka.produce("docs.parse.failed", {
                    "user_id": msg.get("user_id"),
                    "file_id": file_id
                }, key=key or file_id)
                return

        try:
            redis_key = save_text_for_session(session_id=session, file_id=file_id, content=text)
        except Exception:
            logger.exception("Failed to save parsed text for file %s", file_id)
            short = (text or "")[:4000]
            self.kafka.produce("docs.parsed", {
                "user_id": msg.get("user_id"),
                "file_id": file_id,
                "analysis_text": short,
                "session_id": msg.get("session_id")
            }, key=key or file_id)
            return

        add_active_document_local(file_id=file_id, session_id=session)

        self.kafka.produce("docs.parsed", {
            "user_id": msg.get("user_id"),
            "file_id": file_id,
            "redis_key": redis_key,
            "session_id": msg.get("session_id")
        }, key=key or file_id)
        logger.info("Parsed file %s, saved to %s and published to docs.parsed", file_id, redis_key)

    def handle_message(self, topic: str, msg: Dict[str, Any], key: Optional[str]):
        if topic == "docs.uploaded":
            self.process_upload_event(topic, msg, key)
        else:
            logger.warning("Unhandled topic in ParserService: %s", topic)
