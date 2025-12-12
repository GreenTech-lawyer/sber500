import os
import logging
from typing import Optional, Iterable

logger = logging.getLogger("agents_shared.redis_storage")

EXPIRE_TIME = int(os.getenv("EXPIRE_TIME", 7 * 24 * 3600))


def _ensure_redis(r):
    if r:
        return r
    try:
        import redis as _redis
        REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        return _redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        logger.exception("Failed to create redis client from REDIS_URL")
        return None


def safe_get_redis_text(r, redis_key: str) -> Optional[str]:
    try:
        r = _ensure_redis(r)
        if not redis_key or r is None:
            return None
        val = r.get(redis_key)
        if val is None:
            return None
        return str(val)
    except Exception:
        logger.exception("Failed to get key %s from Redis", redis_key)
        return None


def save_analysis_to_redis(r, session_id: str, file_id: str, analysis_text: str, expire: int = EXPIRE_TIME) -> str:
    r = _ensure_redis(r)
    if r is None:
        raise RuntimeError("Redis client not available")
    key = f"analysis:{session_id}:{file_id}"
    try:
        r.set(key, analysis_text)
        r.expire(key, expire)
        return key
    except Exception:
        logger.exception("Failed to save analysis to redis for file %s (session=%s)", file_id, session_id)
        raise


def get_active_documents_for_session(r, session_id: str) -> Iterable[str]:
    try:
        r = _ensure_redis(r)
        if not session_id or r is None:
            return []
        return r.smembers(f"session:{session_id}:active_docs") or []
    except Exception:
        logger.exception("Failed to get active documents for session %s", session_id)
        return []


def get_analysis_from_redis(r, session_id: str, file_id: str) -> Optional[str]:
    key = f"analysis:{session_id}:{file_id}"
    return safe_get_redis_text(r, key)


def save_followup_result(r, redis_key: str, result: str, expire: int = EXPIRE_TIME):
    r = _ensure_redis(r)
    if r is None:
        raise RuntimeError("Redis client not available")
    try:
        r.set(redis_key, result)
        r.expire(redis_key, expire)
    except Exception:
        logger.exception("Failed to save followup result to redis for key %s", redis_key)
        raise


def add_active_document(r, session_id: str, file_id: str) -> None:
    r = _ensure_redis(r)
    try:
        if not session_id or not file_id or r is None:
            return
        r.sadd(f"session:{session_id}:active_docs", file_id)
    except Exception:
        logger.exception("Failed to add active document %s to session %s", file_id, session_id)


def save_text(r, session_id: str, file_id: str, content: str, prefix: str = "doc:text", expire: int = EXPIRE_TIME) -> str:
    r = _ensure_redis(r)
    if r is None:
        raise RuntimeError("Redis client not available")
    key = f"{prefix}:{session_id}:{file_id}"
    try:
        r.set(key, content)
        r.expire(key, expire)
        return key
    except Exception:
        logger.exception("Failed to save text to redis key %s", key)
        raise


def sismember(r, session_id: str, member: str) -> bool:
    try:
        r = _ensure_redis(r)
        if not session_id or not member or r is None:
            return False
        return r.sismember(f"session:{session_id}:active_docs", member)
    except Exception:
        logger.exception("Failed to check membership for %s in session %s", member, session_id)
        return False
