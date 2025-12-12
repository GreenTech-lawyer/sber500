from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# Активные соединения: user_id -> list[WebSocket]
_active: dict[str, list[WebSocket]] = {}


def save_connection(user_id: str, ws: WebSocket):
    conns = _active.get(user_id)
    if conns is None:
        conns = []
        _active[user_id] = conns
    conns.append(ws)
    # import bridge lazily to avoid circular imports at module load time
    try:
        from api.kafka_ws_bridge import bridge

        # ask bridge to flush any buffered messages for this user
        bridge.flush_user(user_id)
    except Exception:
        # if bridge isn't ready or import fails, just ignore — bridge will flush later
        pass


def drop_connection(user_id: str, ws: WebSocket | None = None):
    conns = _active.get(user_id)
    if not conns:
        return
    if ws is None:
        # drop all
        _active.pop(user_id, None)
        return
    try:
        conns.remove(ws)
    except ValueError:
        pass
    if not conns:
        _active.pop(user_id, None)


def get_connections(user_id: str) -> list[WebSocket]:
    return list(_active.get(user_id) or [])


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    save_connection(user_id, websocket)

    try:
        while True:
            # Ожидание сообщения от клиента
            data = await websocket.receive_json()
            print(f"Received message: {data}")
            # пока эхо
            response = {"text": f"Echo: {data.get('text')}"}
            await websocket.send_json(response)
    except WebSocketDisconnect:
        drop_connection(user_id, websocket)
        print(f"User {user_id} disconnected")
