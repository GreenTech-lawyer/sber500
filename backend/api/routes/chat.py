from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents_shared.kafka_client import KafkaClient
from agents_shared.envelope import create_envelope, validate_envelope
from api.connections import save_connection, drop_connection
from api.kafka_ws_bridge import bridge
from sqlmodel import Session, select
from db import engine
from models.message import Message
import asyncio
import logging

router = APIRouter()

REQUEST_TOPIC = "user.message"
producer = KafkaClient(group_id="api-producer-group", topics=[], client_id="api-producer")


def _produce_sync(message: dict, user_id: str):
    """
    Вынесенная синхронная функция — она будет выполняться в отдельном потоке
    чтобы не блокировать asyncio event loop.
    message expected to be a dict containing at least 'text' and optional 'documents' list.
    """
    # normalize payload
    payload = {}
    if isinstance(message, dict):
        payload["text"] = message.get("text")
        if "documents" in message:
            payload["documents"] = message.get("documents")
        # preserve any other keys under payload.raw
        for k, v in message.items():
            if k not in ("text", "documents"):
                payload.setdefault("meta", {})[k] = v
    else:
        payload["text"] = str(message)

    envelope = create_envelope(
        user_id=user_id,
        session_id=payload.get("session_id"),
        source="ws-gateway",
        event="user.message",
        payload=payload,
    )

    # optional validation
    try:
        validate_envelope(envelope)
    except Exception:
        logging.exception("Invalid envelope")
        return

    producer.produce(
        REQUEST_TOPIC,
        envelope,
        key=envelope["correlation_id"]
    )


@router.websocket("/chat/{user_id}")
async def chat_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()
    save_connection(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message")

            if not message:
                await websocket.send_json({"error": "no message provided"})
                continue

            try:
                # persist user message to DB synchronously (don't block loop for long)
                try:
                    text = message.get("text") if isinstance(message, dict) else str(message)
                    with Session(engine) as session:
                        m = Message(user_id=str(user_id), correlation_id=None, direction="user", text=text, payload=message if isinstance(message, dict) else None)
                        session.add(m)
                        session.commit()
                except Exception:
                    logging.exception("Failed to persist user message for user %s", user_id)

                await asyncio.to_thread(_produce_sync, message, user_id)

            except Exception as e:
                logging.exception("Kafka produce failed")
                await websocket.send_json({"error": "internal server error"})
                continue

    except WebSocketDisconnect:
        drop_connection(user_id)
        logging.info(f"User {user_id} disconnected")


@router.get("/chat/history/{user_id}")
async def get_chat_history(user_id: str):
    # Read last 200 messages for this user ordered by created_at asc
    try:
        with Session(engine) as session:
            stmt = select(Message).where(Message.user_id == str(user_id)).order_by(Message.created_at)
            results = session.exec(stmt).all()
            history = []
            for m in results:
                history.append({
                    "id": str(m.id),
                    "type": "user" if m.direction == "user" else "bot",
                    "text": m.text,
                    "ts": int(m.created_at.timestamp() * 1000),
                    "payload": m.payload or {},
                })
        return {"user_id": user_id, "history": history}
    except Exception:
        logging.exception("Failed to load chat history for %s", user_id)
        return {"user_id": user_id, "history": []}
