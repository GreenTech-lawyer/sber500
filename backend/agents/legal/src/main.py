import os
import time
import signal
import logging
from typing import Dict, Any, Optional

import redis
from requests.exceptions import RequestException

from agents_shared.kafka_client import KafkaClient
from .prompts import render
from .llm_client import call_llm, LLMResponse

EXPIRE_TIME = 7 * 24 * 3600

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "legal-group")
CONSUME_TOPICS = os.getenv("CONSUME_TOPICS", "docs.parsed").split(",")
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "analysis.completed")
MAX_RETRIES = int(os.getenv("LLM_RETRIES", "3"))
RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "1.5"))  # seconds multiplier
SNIPPET_LENGTH = int(os.getenv("SNIPPET_LENGTH", "1000"))

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("legal")

# Redis client
r = redis.from_url(REDIS_URL, decode_responses=True)

kafka_client = KafkaClient(
    group_id=KAFKA_GROUP_ID,
    topics=CONSUME_TOPICS,
    client_id="legal"
)

# Flag для graceful shutdown
_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    logger.info("Received signal %s, shutting down...", signum)
    _should_stop = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

def safe_get_redis_text(redis_key: str) -> Optional[str]:
    """Попытка получить текст из Redis, обработка ошибок."""
    try:
        val = r.get(redis_key)
        if val is None:
            logger.warning("Redis key %s not found", redis_key)
            return None
        return str(val)
    except Exception:
        logger.exception("Failed to get key %s from Redis", redis_key)
        return None


def save_analysis_to_redis(file_id: str, analysis_text: str) -> str:
    """Сохраняет анализ в Redis и возвращает ключ."""
    import uuid
    key = f"analysis:{file_id}:{uuid.uuid4().hex}"
    try:
        r.set(key, analysis_text)
        r.expire(key, EXPIRE_TIME)
        return key
    except Exception:
        logger.exception("Failed to save analysis to redis for file %s", file_id)
        raise


def call_llm_with_retries(payload: Dict[str, Any], max_retries: int = MAX_RETRIES) -> LLMResponse:
    """Вызывать LLM с retry и экспоненциальным бэкоффом."""
    attempt = 0
    while True:
        try:
            attempt += 1
            logger.debug("Calling LLM attempt %d payload keys=%s", attempt, list(payload.keys()))
            resp = call_llm(payload)
            # ожидаем, что resp содержит {'text': '...', 'id': '...'} или подобное
            return resp
        except RequestException as e:
            logger.warning("LLM request exception on attempt %d: %s", attempt, e)
        except Exception as e:
            logger.exception("LLM call error on attempt %d: %s", attempt, e)

        if attempt >= max_retries:
            logger.error("LLM failed after %d attempts", attempt)
            raise RuntimeError("LLM failed after retries")
        backoff = RETRY_BACKOFF_BASE ** attempt
        logger.info("Backing off for %.1f seconds before retrying LLM (attempt %d)", backoff, attempt + 1)
        time.sleep(backoff)


def handle_message(topic: str, msg: Dict[str, Any], key: Optional[str] = None):
    """
    Ожидаемый msg: {'redis_key': '...', 'file_id': '...'}.
    Могут быть дополнительные поля: correlation_id, metadata и т.п.
    """
    correlation_id = msg.get("correlation_id") or key or msg.get("file_id") or "unknown"
    logger.info("Handling docs.parsed message correlation_id=%s", correlation_id)

    redis_key = msg.get("redis_key")
    file_id = msg.get("file_id") or "unknown_file"

    if not redis_key:
        logger.error("Message missing redis_key. Ignoring. msg=%s", msg)
        return

    text = safe_get_redis_text(redis_key)
    if not text:
        logger.error("No text found for redis_key=%s; skipping file_id=%s", redis_key, file_id)
        return

    # формируем сниппет для промпта (чтобы не посылать огромный документ)
    snippet = text[:SNIPPET_LENGTH]
    prompt_text = render("legal_review", snippet=snippet)

    payload = {
        "prompt": prompt_text,
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1500")),
        "metadata": {"file_id": file_id, "correlation_id": correlation_id}
    }

    try:
        llm_resp = call_llm_with_retries(payload)
    except Exception as e:
        logger.exception("LLM processing failed for file %s, correlation_id=%s", file_id, correlation_id)
        # публикуем ошибку в Kafka для мониторинга/перепроцессинга
        kafka_client.produce("analysis.failed", {
            "user_id": msg.get("user_id"),
            "file_id": file_id,
            "redis_key": redis_key,
            "reason": str(e),
            "correlation_id": correlation_id
        }, key=correlation_id)
        return

    # ожидаем текст в llm_resp['text'] или 'result'
    analysis_text = llm_resp.text

    try:
        analysis_key = save_analysis_to_redis(file_id, analysis_text)
    except Exception:
        # если не удалось сохранить в redis — публикуем краткий результат прямо в Kafka (если маленький)
        short_text = analysis_text[:2000]
        kafka_client.produce(PRODUCE_TOPIC, {
            "user_id": msg.get("user_id"),
            "file_id": file_id,
            "analysis_key": None,
            "analysis_text": short_text,
            "correlation_id": correlation_id
        }, key=correlation_id)
        logger.warning(f"Saved short analysis to '{PRODUCE_TOPIC}' because redis save failed.")
        return

    # publish completed event
    kafka_client.produce(PRODUCE_TOPIC, {
        "user_id": msg.get("user_id"),
        "file_id": file_id,
        "analysis_key": analysis_key,
        "correlation_id": correlation_id
    }, key=correlation_id)
    logger.info(f"Published {PRODUCE_TOPIC} for file %s (analysis_key=%s)", file_id, analysis_key)


def main_loop():
    logger.info("Legal agent started. Subscribed to topics: %s", CONSUME_TOPICS)

    kafka_client.on_message = handle_message

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
