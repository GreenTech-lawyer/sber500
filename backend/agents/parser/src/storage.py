import logging
import os
import uuid
import redis

logger = logging.getLogger("parser.storage")


REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
REDIS_TTL = int(os.getenv("REDIS_TTL_SECONDS", str(7 * 24 * 3600)))

r = redis.from_url(REDIS_URL, decode_responses=True)


def save_text(id_hint: str, content: str) -> str:
    key = f"doc:text:{id_hint}:{uuid.uuid4().hex}"
    r.set(key, content)
    r.expire(key, REDIS_TTL)
    logger.debug("Saved text to redis key=%s size=%d", key, len(content) if content else 0)
    return key


def get_text(key: str) -> str:
    val = r.get(key)
    if val is None:
        raise KeyError(f"Redis key {key} not found")
    return str(val)
