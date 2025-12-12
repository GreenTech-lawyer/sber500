import os
import time
import signal
import logging
from typing import Dict, Any, Optional

import redis

from agents_shared.kafka_client import KafkaClient
from .service import LegalService

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "legal-group")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "docs.parsed,legal.followup.requested").split(",")
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "analysis.completed")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("legal")

r = redis.from_url(REDIS_URL, decode_responses=True)

kafka_client = KafkaClient(
    group_id=KAFKA_GROUP_ID,
    topics=CONSUME_TOPICS,
    client_id="legal"
)

service = LegalService(redis_client=r, kafka_client=kafka_client)

_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, shutting down...", signum)
    _should_stop = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main_loop():
    logger.info("Legal agent started. Subscribed to topics: %s", CONSUME_TOPICS)

    kafka_client.on_message = service.handle_message

    try:
        kafka_client.listen_forever(poll_timeout=1.0)
    except KeyboardInterrupt:
        logger.info("Legal interrupted by user")
    except Exception as e:
        logger.exception("Unexpected legal main loop error: %s", e)
    finally:
        logger.info("Legal agent stopped.")


if __name__ == "__main__":
    main_loop()
