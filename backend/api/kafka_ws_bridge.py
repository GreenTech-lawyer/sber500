import asyncio
import logging
from agents_shared.kafka_client import KafkaClient
from .connections import get_connection

logger = logging.getLogger("kafka_ws_bridge")

RESPONSE_TOPIC = "assistant_responses"
GROUP = "ws-bridge-group"

class KafkaWSBridge:
    def __init__(self, bootstrap=None):
        self.client = KafkaClient(group_id=GROUP, topics=[RESPONSE_TOPIC], client_id="ws-bridge")
        self.client.on_message = self.on_kafka_message

    def start_in_background(self):
        loop = asyncio.get_event_loop()
        # запускаем блокирующий consumer в отдельном thread via executor
        loop.run_in_executor(None, self.client.listen_forever)

    def on_kafka_message(self, topic: str, value: dict, key: str | None):
        """
        Этот метод вызывается в потоке consumer-а (не в asyncio loop).
        Нам нужно отправить сообщение в websocket — делаем через loop.call_soon_threadsafe.
        """
        user_id = value.get("user_id")
        reply = value.get("reply") or value.get("text") or value.get("draft")

        loop = asyncio.get_event_loop()
        conn = get_connection(user_id)
        if conn is None:
            logger.debug("No active WS for user %s", user_id)
            return

        # отправляем через loop, т.к. conn.send_json — корутина
        async def _send():
            try:
                await conn.send_json({"reply": reply})
            except Exception:
                logger.exception("Failed to send reply to user %s", user_id)

        loop.call_soon_threadsafe(asyncio.create_task, _send())

bridge = KafkaWSBridge()
