import os
import logging
import signal

from minio import Minio

from agents_shared.kafka_client import KafkaClient

from .service import ParserService

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

service = ParserService(minio_client=minio_client, kafka_producer=kafka_client)

_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, stopping", signum)
    _should_stop = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main_loop():
    logger.info("Parser agent started. Listening topics: %s", CONSUME_TOPICS)

    kafka_client.on_message = service.handle_message

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
