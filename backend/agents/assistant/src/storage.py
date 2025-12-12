import logging

from agents_shared.redis_storage import get_active_documents_for_session, save_text

logger = logging.getLogger("assistant.storage")


class AssistantStorage:
    def __init__(self, redis_client):
        self.r = redis_client

    def session_has_active_docs(self, session_id: str) -> bool:
        try:
            docs = get_active_documents_for_session(self.r, session_id)
            return bool(docs)
        except Exception:
            logger.exception("Error while getting active documents for session %s", session_id)
            return False

    def save_llm_response(self, content: str, session_id: str = "assistant", file_id: str = None) -> str:
        # file_id is optional; create a generated key using save_text prefix
        # reuse save_text helper which returns a key
        if file_id is None:
            file_id = "response"
        return save_text(self.r, session_id, file_id, content, prefix="llm_assistant_response")
