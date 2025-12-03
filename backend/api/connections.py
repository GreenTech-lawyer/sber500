from fastapi import WebSocket

_active: dict[str, WebSocket] = {}

def save_connection(user_id: str, ws: WebSocket):
    _active[user_id] = ws

def drop_connection(user_id: str):
    _active.pop(user_id, None)

def get_connection(user_id: str) -> WebSocket | None:
    return _active.get(user_id)
