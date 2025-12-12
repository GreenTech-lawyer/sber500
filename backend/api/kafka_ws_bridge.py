import asyncio
import logging
import threading
from collections import deque
from typing import Dict, Any
from agents_shared.kafka_client import KafkaClient
from agents_shared.envelope import unwrap_payload_or_legacy
# use new get_connections to support multiple ws per user
from .connections import get_connections

# DB imports
from sqlmodel import Session
from db import engine
from models.message import Message

logger = logging.getLogger("kafka_ws_bridge")

RESPONSE_TOPIC = "assistant.response"
GROUP = "ws-bridge-group"


class KafkaWSBridge:
    def __init__(self, bootstrap=None):
        # kafka client runs in its own (threaded) consumer
        self.client = KafkaClient(group_id=GROUP, topics=[RESPONSE_TOPIC], client_id="ws-bridge")
        # message handler will be invoked from the consumer thread
        self.client.on_message = self.on_kafka_message

        # will be set to the asyncio event loop used by FastAPI at startup
        self.loop: asyncio.AbstractEventLoop | None = None

        # per-user buffers for messages that arrive before WS is connected
        self._buffers: Dict[str, deque] = {}
        self._buffers_lock = threading.Lock()
        self.max_buffer_messages = 200

    def start_in_background(self):
        """
        Capture the running event loop and start the blocking Kafka listener in a background thread.
        This must be called from the FastAPI startup handler (i.e. from the running loop).
        """
        # get_running_loop will raise if there is no running loop which helps catch misuses
        self.loop = asyncio.get_running_loop()
        # run the blocking kafka consumer in a dedicated daemon thread
        t = threading.Thread(target=self.client.listen_forever, daemon=True)
        t.start()

    def _schedule_create_task(self, coro):
        """Helper to create a task on the event loop thread; used with call_soon_threadsafe(callback, coro)."""
        asyncio.create_task(coro)

    def _prepare_outgoing(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        # normalize message for frontend: include envelope and top-level text/reply if present
        payload = envelope.get("payload", {}) or {}
        return {
            "envelope": envelope,
            "text": payload.get("text"),
            "reply": payload.get("reply"),
        }

    def _buffer_message(self, user_id: str, msg: Dict[str, Any]):
        with self._buffers_lock:
            q = self._buffers.get(user_id)
            if q is None:
                q = deque()
                self._buffers[user_id] = q
            q.append(msg)
            # trim if buffer grows too large
            while len(q) > self.max_buffer_messages:
                q.popleft()

    def flush_user(self, user_id: str) -> None:
        """
        Called when a websocket connection for `user_id` is established.
        This method may be called from the asyncio loop or from another thread (we'll schedule on the loop).
        """
        if not self.loop:
            # loop not captured yet — nothing to do
            return

        # Schedule the async flush on the running loop in a thread-safe way
        # schedule the task creation on the loop thread-safely, pass coroutine as arg to avoid analyzer warnings
        self.loop.call_soon_threadsafe(self._schedule_create_task, self._flush_user_async(user_id))

    async def _flush_user_async(self, user_id: str):
        # pop buffer under lock
        with self._buffers_lock:
            q = self._buffers.pop(user_id, None)
        if not q:
            return

        conns = get_connections(user_id)
        if not conns:
            # connection vanished — re-buffer messages
            with self._buffers_lock:
                self._buffers.setdefault(user_id, deque()).extendleft(reversed(q))
            return

        # send buffered messages sequentially to all connections; on failure, re-buffer remaining
        try:
            while q:
                msg = q.popleft()
                # attempt to send to all connections; if any fails, re-buffer for retry
                failed = False
                for conn in list(conns):
                    try:
                        await conn.send_json(msg)
                    except Exception:
                        logger.exception("Failed to send buffered message to user %s on conn %s", user_id, conn)
                        failed = True
                if failed:
                    # put current msg and remaining back to buffer and stop
                    with self._buffers_lock:
                        dq = self._buffers.setdefault(user_id, deque())
                        dq.appendleft(msg)
                        while q:
                            dq.appendleft(q.pop())
                    return
        except Exception:
            logger.exception("Unexpected error while flushing buffer for user %s", user_id)

    def on_kafka_message(self, topic: str, value: Dict[str, Any], key: str | None):
        """
        Called from Kafka consumer thread. Schedule sending or buffer if no connection.
        Also persist bot message into DB.
        """
        try:
            envelope, _ = unwrap_payload_or_legacy(value)
        except Exception:
            logger.exception("Failed to unwrap message from Kafka")
            return

        user_id = envelope.get("user_id")
        if not user_id:
            # No target user -> nothing to deliver to WS
            logger.debug("Received envelope without user_id: %s", envelope)
            return

        out_msg = self._prepare_outgoing(envelope)

        # Persist message to DB (do not block delivery on DB errors)
        try:
            text = (envelope.get("payload") or {}).get("text") or (envelope.get("payload") or {}).get("reply")
            with Session(engine) as session:
                m = Message(user_id=str(user_id), correlation_id=envelope.get("correlation_id"), direction="bot", text=text, payload=envelope.get("payload"))
                session.add(m)
                session.commit()
        except Exception:
            logger.exception("Failed to persist message for user %s", user_id)

        # Ensure we have the loop reference
        if not self.loop:
            # not started yet - buffer the message
            logger.debug("Loop not ready, buffering message for user %s", user_id)
            self._buffer_message(user_id, out_msg)
            return

        # try to get active connections
        conns = get_connections(user_id)
        if not conns:
            logger.debug("No active WS for user %s, buffering", user_id)
            self._buffer_message(user_id, out_msg)
            return

        # schedule sending on the captured loop
        async def _send_to_all():
            failed_any = False
            for conn in list(conns):
                try:
                    await conn.send_json(out_msg)
                except Exception:
                    logger.exception("Failed to send envelope to user %s on conn %s", user_id, conn)
                    failed_any = True
            if failed_any:
                # buffer for retry
                self._buffer_message(user_id, out_msg)

        # schedule create_task in a thread-safe way
        try:
            # schedule by passing callback and coroutine as arg
            self.loop.call_soon_threadsafe(self._schedule_create_task, _send_to_all())
        except Exception:
            logger.exception("Failed to schedule send task for user %s, buffering", user_id)
            self._buffer_message(user_id, out_msg)


bridge = KafkaWSBridge()
