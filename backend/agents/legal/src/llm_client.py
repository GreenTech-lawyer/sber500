import os
import logging
import time
from typing import NamedTuple, Optional, Dict, Any
from gigachat import GigaChat
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

GIGA_CREDENTIALS = os.getenv("GIGA_CHAT_CREDENTIALS")
VERIFY_SSL = os.getenv("GIGA_CHAT_VERIFY_SSL", "false").lower() == "true"
MAX_RETRIES = int(os.getenv("LLM_RETRIES", "3"))
RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "1.5"))


class LLMResponse(NamedTuple):
    text: str
    id: Optional[str]
    metadata: dict


def call_llm(payload: dict) -> LLMResponse:
    """
    Адаптация call_llm для GigaChat API с возвратом NamedTuple.
    payload должен содержать ключ 'prompt'.
    """
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("Payload must contain 'prompt' key")

    try:
        with GigaChat(credentials=GIGA_CREDENTIALS, verify_ssl_certs=VERIFY_SSL) as giga:
            response = giga.chat(prompt)
            content = response.choices[0].message.content
            return LLMResponse(
                text=content,
                id=getattr(response, "id", None),
                metadata=payload.get("metadata", {})
            )
    except Exception as e:
        logger.exception("GigaChat API call failed")
        raise RequestException(f"GigaChat API call failed: {e}") from e


def call_llm_with_retries(payload: Dict[str, Any], max_retries: Optional[int] = None) -> LLMResponse:
    if max_retries is None:
        max_retries = MAX_RETRIES
    attempt = 0
    while True:
        try:
            attempt += 1
            logger.debug("Calling LLM attempt %d payload keys=%s", attempt, list(payload.keys()))
            return call_llm(payload)
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
