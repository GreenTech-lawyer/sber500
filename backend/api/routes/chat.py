from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents_shared.kafka_client import KafkaClient

from api.connections import save_connection, drop_connection
from api.kafka_ws_bridge import bridge

router = APIRouter()

REQUEST_TOPIC = "assistant_requests"
producer = KafkaClient(group_id="api-producer-group", topics=[], client_id="api-producer")

@router.on_event("startup")
async def startup():
    bridge.start_in_background()

@router.websocket("/chat/{user_id}")
async def chat_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()
    save_connection(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message")
            if message is None:
                await websocket.send_json({"error": "no message provided"})
                continue
            producer.produce(REQUEST_TOPIC, {"user_id": user_id, "message": message}, key=user_id)
    except WebSocketDisconnect:
        drop_connection(user_id)
