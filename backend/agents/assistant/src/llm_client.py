import os
import logging
from typing import NamedTuple, Optional
from gigachat import GigaChat
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

GIGA_CREDENTIALS = os.getenv("GIGA_CHAT_CREDENTIALS")
VERIFY_SSL = os.getenv("GIGA_CHAT_VERIFY_SSL", "false").lower() == "true"


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

