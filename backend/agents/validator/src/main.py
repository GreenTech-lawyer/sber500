import os
import signal
import logging
from typing import Optional, Dict

from agents_shared.kafka_client import KafkaClient
from .checker import DraftChecker

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "draft.created").split(",")
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "draft.approved")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("validator")

kafka_client = KafkaClient(
    group_id="validator-group",
    topics=CONSUME_TOPICS,
    client_id="validator"
)

_should_stop = False

def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, shutting down...", signum)
    _should_stop = True

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def handle_message(topic: str, raw: Dict, key: Optional[str] = None):
    """
    Проверяет драфт и решает, публиковать ли.
    """
    text = raw.get("draft", "")
    user_id = raw.get("user_id")

    if DraftChecker.check_text(text):
        logger.info("Draft approved for user_id=%s", user_id)
        output = {"user_id": user_id, "draft": text, "status": "approved"}
        kafka_client.produce(PRODUCE_TOPIC, output, key=key)
    else:
        logger.info("Draft rejected for user_id=%s", user_id)
        output = {"user_id": user_id, "draft": text, "status": "rejected"}
        kafka_client.produce("draft.rejected", output, key=key)


kafka_client.on_message = handle_message


def main_loop():
    logger.info("Validator agent started. Listening topics: %s", CONSUME_TOPICS)
    try:
        kafka_client.listen_forever(poll_timeout=1.0)
    except Exception as e:
        logger.exception("Unexpected validator main loop error: %s", e)
    finally:
        logger.info("Validator agent stopped.")


if __name__ == "__main__":
    main_loop()
