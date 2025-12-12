import logging
import os

logger = logging.getLogger("parser.storage")


from agents_shared.redis_storage import save_text, add_active_document, get_active_documents_for_session


def save_text_for_session(session_id: str, file_id: str, content: str) -> str:
    return save_text(None, session_id=session_id, file_id=file_id, content=content)


def add_active_document_local(file_id: str, session_id: str) -> None:
    return add_active_document(None, session_id=session_id, file_id=file_id)


def get_active_documents_for_session_local(session_id: str):
    return get_active_documents_for_session(None, session_id=session_id)
