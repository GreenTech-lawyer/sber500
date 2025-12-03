import os
import signal
import logging
from typing import Optional, Dict
import redis

from agents_shared.kafka_client import KafkaClient
from .dialogue import AssistantFormatter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "analysis.completed,user.message").split(",")
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "draft.created")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("assistant")

r = redis.from_url(REDIS_URL, decode_responses=True)

kafka_client = KafkaClient(
    group_id="assistant-group",
    topics=CONSUME_TOPICS,
    client_id="assistant"
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
    Диспетчер обработки разных типов входящих событий.
    """
    if topic == "analysis.completed":
        text = r.get(raw["analysis_key"])
        formatted = AssistantFormatter.format_user_message(text)
        output = {
            "user_id": raw.get("user_id"),
            "draft": formatted,
            "source": "assistant"
        }
        kafka_client.produce(PRODUCE_TOPIC, output, key=key)

    elif topic == "user.message":
        formatted = AssistantFormatter.format_user_message(raw.get("text", ""))
        output = {
            "user_id": raw.get("user_id"),
            "draft": formatted,
            "source": "assistant"
        }
        kafka_client.produce(PRODUCE_TOPIC, output, key=key)

    else:
        logger.warning("Unknown topic: %s", topic)


kafka_client.on_message = handle_message


def main_loop():
    logger.info("Assistant agent started. Listening topics: %s", CONSUME_TOPICS)
    try:
        kafka_client.listen_forever(poll_timeout=1.0)
    except Exception as e:
        logger.exception("Unexpected assistant main loop error: %s", e)
    finally:
        logger.info("Assistant agent stopped.")


if __name__ == "__main__":
    main_loop()
