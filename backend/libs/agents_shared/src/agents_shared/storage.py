"""Unified Redis storage helpers for agents.
"""
from typing import Optional
import redis

# Usage: pass redis_client from deps.py or service

def safe_get_redis_text(redis_client: redis.Redis, key: str) -> Optional[str]:
    try:
        value = redis_client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
    except Exception:
        return None


def save_text(redis_client: redis.Redis, key: str, text: str, expire: int = 3600) -> bool:
    try:
        redis_client.set(key, text, ex=expire)
        return True
    except Exception:
        return False

