import os
import signal
import logging
import redis

from agents_shared.kafka_client import KafkaClient
from .dialogue import AssistantFormatter
from .prompts import render
from .service import AssistantService

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "analysis.completed,user.message").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "assistant-group")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("assistant")

r = redis.from_url(REDIS_URL, decode_responses=True)

kafka_client = KafkaClient(
    group_id=KAFKA_GROUP_ID,
    topics=CONSUME_TOPICS,
    client_id="assistant"
)

service = AssistantService(redis_client=r, kafka_client=kafka_client, formatter=AssistantFormatter, prompts_render=render)

_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, shutting down...", signum)
    _should_stop = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


kafka_client.on_message = service.handle_message


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
