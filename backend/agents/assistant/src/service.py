import os
import time
import logging
from typing import Optional, Dict, Any

from agents_shared.redis_storage import safe_get_redis_text
from .storage import AssistantStorage
from .llm_client import call_llm, LLMResponse

logger = logging.getLogger("assistant.service")

MAX_RETRIES = int(os.getenv("LLM_RETRIES", "3"))
RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "1.5"))
SNIPPET_LENGTH = int(os.getenv("SNIPPET_LENGTH", "1000"))
PRODUCE_TOPIC = os.getenv("PRODUCE_TOPIC", "assistant.response")


class AssistantService:
    def __init__(self, redis_client, kafka_client, formatter, prompts_render):
        self.r = redis_client
        self.kafka = kafka_client
        self.formatter = formatter
        self.render = prompts_render

    def _call_llm_with_retries(self, payload: Dict[str, Any], max_retries: int = MAX_RETRIES) -> LLMResponse:
        attempt = 0
        while True:
            try:
                attempt += 1
                logger.debug("Calling LLM attempt %d payload keys=%s", attempt, list(payload.keys()))
                resp = call_llm(payload)
                return resp
            except Exception as e:
                logger.exception("LLM call error on attempt %d: %s", attempt, e)

            if attempt >= max_retries:
                logger.error("LLM failed after %d attempts", attempt)
                raise RuntimeError("LLM failed after retries")
            backoff = RETRY_BACKOFF_BASE ** attempt
            logger.info("Backing off for %.1f seconds before retrying LLM (attempt %d)", backoff, attempt + 1)
            time.sleep(backoff)

    def handle_analysis_completed(self, raw: Dict[str, Any], correlation_id: str):
        redis_key = raw.get("analysis_key")
        text = safe_get_redis_text(self.r, redis_key)
        if not text:
            logger.error("No text found for analysis_key=%s; skipping", redis_key)
            return
        formatted = self.formatter.format_analysis(text)
        output = {
            "user_id": raw.get("user_id"),
            "text": formatted,
            "source": "assistant",
            "analysis_key": redis_key,
            "correlation_id": correlation_id,
        }
        self.kafka.produce(PRODUCE_TOPIC, output, key=correlation_id)

    def handle_user_message(self, raw: Dict[str, Any], correlation_id: str):
        user_text = raw.get("text", "")
        session_id = raw.get("session_id")

        storage = AssistantStorage(self.r)

        # If session has any active documents, delegate to legal agent
        try:
            if session_id and storage.session_has_active_docs(session_id):
                self.kafka.produce(
                    "legal.followup.requested",
                    {"text": user_text, "session_id": session_id},
                    key=correlation_id,
                )
                return
        except Exception:
            logger.exception("Failed to check Redis session active docs; falling back to local processing")

        snippet = user_text[:SNIPPET_LENGTH]
        prompt_text = self.render("assistant_reply", snippet=snippet)

        payload = {
            "prompt": prompt_text,
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "800")),
            "metadata": {"user_id": raw.get("user_id"), "correlation_id": correlation_id},
        }

        try:
            llm_resp = self._call_llm_with_retries(payload)
        except Exception as e:
            logger.exception("LLM processing failed for user %s, correlation_id=%s", raw.get("user_id"), correlation_id)
            self.kafka.produce("chat.error", {"user_id": raw.get("user_id"), "reason": str(e), "correlation_id": correlation_id}, key=correlation_id)
            return

        llm_response = llm_resp.text

        try:
            # save followup result key is handled by storage helper
            key = storage.save_llm_response(llm_response)
        except Exception:
            short_text = llm_response[:2000]
            self.kafka.produce(PRODUCE_TOPIC, {"user_id": raw.get("user_id"), "text": self.formatter.format_analysis(short_text), "analysis_key": None, "correlation_id": correlation_id}, key=correlation_id)
            logger.warning("Saved short draft to '%s' because redis save failed.", PRODUCE_TOPIC)
            return

        self.kafka.produce(PRODUCE_TOPIC, {"user_id": raw.get("user_id"), "text": self.formatter.format_analysis(llm_response), "analysis_key": key, "correlation_id": correlation_id}, key=correlation_id)

    def handle_message(self, topic: str, raw: Dict[str, Any], key: Optional[str] = None):
        correlation_id = raw.get("correlation_id") or key or raw.get("user_id") or "unknown"
        if topic == "analysis.completed":
            self.handle_analysis_completed(raw, correlation_id)
        elif topic == "user.message":
            self.handle_user_message(raw, correlation_id)
        else:
            logger.warning("Unknown topic: %s", topic)
