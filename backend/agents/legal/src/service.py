import os
import logging
from typing import Dict, Any, Optional
import hashlib
import redis
from agents_shared.kafka_client import KafkaClient
from agents_shared.storage import safe_get_redis_text
from agents_shared.envelope import create_envelope, validate_envelope, unwrap_payload_or_legacy
from .prompts import render
from .llm_client import call_llm_with_retries

logger = logging.getLogger("legal.service")

EXPIRE_TIME = int(os.getenv("EXPIRE_TIME", 7 * 24 * 3600))
SNIPPET_LENGTH = int(os.getenv("SNIPPET_LENGTH", "1000"))

MENU_PROMPTS = {
    # example: 'risk_summary': 'legal_review'
}


class LegalService:
    def __init__(self, redis_client: redis.Redis, kafka_client: KafkaClient):
        self.r = redis_client
        self.kafka = kafka_client

    def handle_docs_parsed(self, envelope: Dict[str, Any]):
        payload = envelope["payload"]
        correlation_id = envelope["correlation_id"]
        session_id = envelope.get("session_id")
        user_id = envelope.get("user_id")
        redis_key = payload.get("redis_key") or payload.get("redis_key_text") or payload.get("analysis_redis_key")
        file_id = payload.get("file_id") or "unknown_file"
        logger.info(f"Handling docs.parsed event correlation_id={correlation_id}")
        if not redis_key:
            logger.error(f"Message missing redis_key. Ignoring. envelope={envelope}")
            return
        text = safe_get_redis_text(self.r, redis_key)
        if not text:
            logger.error(f"No text found for redis_key={redis_key}; skipping file_id={file_id}")
            return
        snippet = text[:SNIPPET_LENGTH]
        prompt_text = render("legal_review", snippet=snippet)
        llm_payload = {
            "prompt": prompt_text,
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1500")),
            "metadata": {"file_id": file_id, "correlation_id": correlation_id}
        }
        try:
            llm_resp = call_llm_with_retries(llm_payload)
        except Exception as e:
            logger.exception(f"LLM processing failed for file {file_id}, correlation_id={correlation_id}")
            error_env = create_envelope(
                user_id=user_id,
                session_id=session_id,
                source="legal",
                event="analysis.failed",
                payload={
                    "file_id": file_id,
                    "redis_key": redis_key,
                    "reason": str(e)
                },
                correlation_id=correlation_id
            )
            self.kafka.produce("analysis.failed", error_env, key=correlation_id)
            return
        analysis_text = llm_resp.text
        # Save analysis to redis omitted for brevity
        analysis_key = f"analysis:{session_id}:{file_id}"  # Example key
        response_env = create_envelope(
            user_id=user_id,
            session_id=session_id,
            source="legal",
            event="analysis.completed",
            payload={
                "file_id": file_id,
                "analysis_key": analysis_key
            },
            correlation_id=correlation_id
        )
        self.kafka.produce("analysis.completed", response_env, key=correlation_id)
        logger.info(f"Published analysis.completed for file {file_id} (analysis_key={analysis_key})")

    def handle_followup_request(self, envelope: Dict[str, Any]):
        payload = envelope["payload"]
        correlation_id = envelope["correlation_id"]
        user_id = envelope.get("user_id")
        session_id = envelope.get("session_id")
        document_id = payload.get("document_id")
        redis_key_text = payload.get("redis_key_text")
        query = payload.get("query")
        query_type = payload.get("query_type", "default")
        # 1. Получаем текст документа из Redis
        doc_text = safe_get_redis_text(self.r, redis_key_text)
        # 2. Получаем предыдущий анализ (если есть)
        prev_analysis = safe_get_redis_text(self.r, payload.get("redis_key_previous_analysis", ""))
        # 3. Формируем промпт в зависимости от типа запроса
        if query_type == "menu":
            prompt = MENU_PROMPTS.get(query, "")
        else:
            prompt = f"Followup: {query}\nDocument: {doc_text}\nPrevious analysis: {prev_analysis}"
        # 4. Отправляем в LLM
        llm_resp = call_llm_with_retries({"prompt": prompt, "max_tokens": 1200})
        result = llm_resp.text
        # 5. Публикуем результат
        followup_env = create_envelope(
            user_id=user_id,
            session_id=session_id,
            source="legal",
            event="legal.followup.completed",
            payload={
                "document_id": document_id,
                "query": query,
                "answer": result,
                "redis_key": f"doc:followup:{document_id}:{hash(query)}"
            },
            correlation_id=correlation_id
        )
        self.kafka.produce("legal.followup.completed", followup_env, key=correlation_id)

    def handle_message(self, topic: str, raw: Dict[str, Any], key: Optional[str] = None):
        envelope, correlation_id = unwrap_payload_or_legacy(raw)
        event = envelope["event"]
        if event == "docs.parsed":
            self.handle_docs_parsed(envelope)
        elif event == "legal.followup.requested":
            self.handle_followup_request(envelope)
        else:
            logger.warning(f"Unknown event: {event}")
