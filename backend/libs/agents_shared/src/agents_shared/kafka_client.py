import json
import logging
from confluent_kafka import Producer, Consumer, KafkaError
from typing import Callable, Optional

from api.deps import KAFKA_BOOTSTRAP

logger = logging.getLogger("shared.kafka")

class KafkaProducer:
    def __init__(self, client_id: str = 'agent-producer'):
        conf = {
            'bootstrap.servers': KAFKA_BOOTSTRAP,
            'client.id': client_id,
            'linger.ms': 5,
        }
        self.p = Producer(conf)

    def produce(self, topic: str, value: dict, key: Optional[str] = None, on_delivery: Optional[Callable] = None):
        data = json.dumps(value).encode('utf-8')
        self.p.produce(topic, value=data, key=key, on_delivery=on_delivery)
        self.p.poll(0)

    def flush(self):
        self.p.flush()


class KafkaConsumer:
    def __init__(self, topics, group_id: str, client_id: str = 'agent-consumer', auto_offset_reset='earliest'):
        conf = {
            'bootstrap.servers': KAFKA_BOOTSTRAP,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': False,
            'client.id': client_id,
        }
        self.c = Consumer(conf)
        if topics:
            self.c.subscribe(topics)

    def consume_loop(self, handler: Callable[[str, dict, Optional[str]], None], poll_timeout=1.0):
        """Бесконечный цикл потребления сообщений"""
        try:
            while True:
                msg = self.c.poll(poll_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error("Consumer error: %s", msg.error())
                    continue

                try:
                    key = msg.key().decode() if msg.key() else None
                    val = json.loads(msg.value().decode('utf-8'))
                    topic = msg.topic()
                    handler(topic, val, key)
                    self.c.commit(msg)
                except Exception:
                    logger.exception("Error handling message")
        finally:
            self.c.close()


class KafkaClient:
    def __init__(
        self,
        group_id: str,
        topics: list,
        client_id: str = 'agent-client',
        on_message: Optional[Callable[[str, dict, Optional[str]], None]] = None
    ):
        self.producer = KafkaProducer(client_id=f"{client_id}-producer")
        self.consumer = KafkaConsumer(
            topics=topics,
            group_id=group_id,
            client_id=f"{client_id}-consumer"
        )
        self.on_message = on_message

    def produce(self, topic: str, value: dict, key: Optional[str] = None):
        """Отправляет сообщение в Kafka"""
        self.producer.produce(topic, value, key=key)
        self.producer.flush()

    def listen_forever(self, poll_timeout: float = 1.0):
        """Запускает бесконечный цикл прослушивания сообщений"""
        if not self.on_message:
            logger.warning("No on_message handler set")
            return

        self.consumer.consume_loop(self.on_message, poll_timeout)
