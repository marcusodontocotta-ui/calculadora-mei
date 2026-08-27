import json
import asyncio
import time
from typing import Callable, Any
from functools import lru_cache
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as aioredis

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("bus")


class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    ACK = "ack"
    NACK = "nack"
    DEAD = "dead"
    RETRY = "retry"


@dataclass
class DeliveryEnvelope:
    message_id: str
    stream_id: str
    event: str
    sender: str
    target: str
    status: DeliveryStatus
    attempts: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    delivered_at: float = 0.0
    acked_at: float = 0.0
    feedback: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageFeedback:
    original_id: str
    responder_id: str
    status: DeliveryStatus
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Event bus com conferidor, feedback e delivery garantido.

    Fluxo:
    1. Agent publica mensagem -> stream
    2. Conferidor valida -> move para fila do destinatario
    3. Destinatario processa -> envia ACK ou NACK
    4. Se NACK -> retry ou dead letter queue
    5. Tudo logado em audit trail
    """

    STREAM_PREFIX = "cupula:stream:"
    DELIVERY_PREFIX = "cupula:delivery:"
    FEEDBACK_PREFIX = "cupula:feedback:"
    DLQ_PREFIX = "cupula:dlq:"
    AUDIT_KEY = "cupula:audit"
    CONSUMER_GROUPS = "cupula:groups"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._running = False
        self._handlers: dict[str, Callable] = {}
        self._feedback_handlers: dict[str, Callable] = {}

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=50,
        )
        await self._redis.ping()
        logger.info("EventBus conectado ao Redis")

    async def disconnect(self):
        self._running = False
        if self._redis:
            await self._redis.close()
            logger.info("EventBus desconectado")

    def _stream_key(self, event: EventType) -> str:
        return f"{self.STREAM_PREFIX}{event.value}"

    def _delivery_key(self, msg_id: str) -> str:
        return f"{self.DELIVERY_PREFIX}{msg_id}"

    def _feedback_key(self, msg_id: str) -> str:
        return f"{self.FEEDBACK_PREFIX}{msg_id}"

    def _dlq_key(self, event: str) -> str:
        return f"{self.DLQ_PREFIX}{event}"

    async def publish(self, event: EventType, message: Message, target: str = ""):
        stream_key = self._stream_key(event)

        envelope = DeliveryEnvelope(
            message_id=message.id,
            stream_id="",
            event=event.value,
            sender=message.sender,
            target=target or "*",
            status=DeliveryStatus.PENDING,
            payload=message.payload,
        )

        data = {
            "id": message.id,
            "sender": message.sender,
            "target": target,
            "content": message.content,
            "timestamp": message.timestamp,
            "event": event.value,
            "payload": json.dumps(message.payload, ensure_ascii=False),
            "envelope": json.dumps({
                "status": "pending",
                "attempts": 0,
                "created_at": envelope.created_at,
            }),
        }

        stream_id = await self._redis.xadd(
            stream_key,
            data,
            maxlen=get_settings().REDIS_STREAM_MAX_LEN,
        )

        envelope.stream_id = stream_id
        await self._redis.setex(
            self._delivery_key(message.id),
            3600,
            json.dumps({
                "message_id": message.id,
                "stream_id": stream_id,
                "event": event.value,
                "sender": message.sender,
                "target": target,
                "status": "pending",
                "attempts": 0,
                "created_at": envelope.created_at,
            }),
        )

        await self._audit_log("publish", event.value, message.id, message.sender, target)

        logger.debug(f"Publicado [{event.value}] id={message.id} target={target}")

        return stream_id

    async def send_with_feedback(
        self,
        event: EventType,
        message: Message,
        target: str,
        timeout: float = 30.0,
    ) -> MessageFeedback:
        """Publica mensagem e aguarda feedback do destinatario."""
        await self.publish(event, message, target=target)

        start_time = time.time()
        while time.time() - start_time < timeout:
            feedback_data = await self._redis.get(self._feedback_key(message.id))
            if feedback_data:
                fb = json.loads(feedback_data)
                return MessageFeedback(
                    original_id=message.id,
                    responder_id=fb.get("responder_id", ""),
                    status=DeliveryStatus(fb.get("status", "ack")),
                    message=fb.get("message", ""),
                    metadata=fb.get("metadata", {}),
                    timestamp=fb.get("timestamp", time.time()),
                )
            await asyncio.sleep(0.1)

        await self._move_to_dlq(event.value, message.id, "timeout aguardando feedback")
        return MessageFeedback(
            original_id=message.id,
            responder_id="",
            status=DeliveryStatus.NACK,
            message="timeout: nenhum feedback recebido",
        )

    async def send_feedback(
        self,
        original_msg_id: str,
        responder_id: str,
        status: DeliveryStatus,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        """Registra feedback para uma mensagem."""
        feedback = MessageFeedback(
            original_id=original_msg_id,
            responder_id=responder_id,
            status=status,
            message=message,
            metadata=metadata or {},
        )

        feedback_data = {
            "responder_id": responder_id,
            "status": status.value,
            "message": message,
            "metadata": json.dumps(metadata or {}),
            "timestamp": feedback.timestamp,
        }

        await self._redis.setex(
            self._feedback_key(original_msg_id),
            3600,
            json.dumps(feedback_data),
        )

        if status == DeliveryStatus.ACK:
            delivery = await self._redis.get(self._delivery_key(original_msg_id))
            if delivery:
                d = json.loads(delivery)
                d["status"] = "acked"
                d["acked_at"] = feedback.timestamp
                await self._redis.setex(self._delivery_key(original_msg_id), 3600, json.dumps(d))

            await self._audit_log("ack", "", original_msg_id, responder_id, "")
            logger.debug(f"ACK recebido para {original_msg_id} de {responder_id}")

        elif status == DeliveryStatus.NACK:
            await self._handle_nack(original_msg_id, responder_id, message)

        elif status == DeliveryStatus.DEAD:
            await self._move_to_dlq("", original_msg_id, message)
            logger.warning(f"Msg {original_msg_id} marcada como DEAD por {responder_id}")

    async def _handle_nack(self, msg_id: str, responder_id: str, reason: str):
        delivery_data = await self._redis.get(self._delivery_key(msg_id))
        if not delivery_data:
            return

        delivery = json.loads(delivery_data)
        delivery["attempts"] = delivery.get("attempts", 0) + 1
        delivery["status"] = "retry"
        delivery["last_nack_reason"] = reason

        if delivery["attempts"] >= delivery.get("max_retries", 3):
            delivery["status"] = "dead"
            await self._move_to_dlq(
                delivery.get("event", ""),
                msg_id,
                f"max retries excedido: {reason}",
            )
            logger.warning(f"Msg {msg_id} movida para DLQ apos {delivery['attempts']} tentativas")
        else:
            logger.info(f"NACK para {msg_id}, tentativa {delivery['attempts']}: {reason}")

        await self._redis.setex(
            self._delivery_key(msg_id), 3600, json.dumps(delivery)
        )
        await self._audit_log("nack", delivery.get("event", ""), msg_id, responder_id, reason)

    async def _move_to_dlq(self, event: str, msg_id: str, reason: str):
        dlq_entry = {
            "message_id": msg_id,
            "event": event,
            "reason": reason,
            "moved_at": time.time(),
        }
        await self._redis.lpush(
            self._dlq_key(event),
            json.dumps(dlq_entry),
        )
        await self._redis.ltrim(self._dlq_key(event), 0, 9999)
        await self._audit_log("dlq", event, msg_id, "", reason)

    async def register_handler(self, event: EventType, handler: Callable):
        self._handlers[event.value] = handler
        logger.info(f"Handler registrado para {event.value}")

    async def register_feedback_handler(self, msg_id: str, handler: Callable):
        self._feedback_handlers[msg_id] = handler

    async def consume_group(
        self,
        event: EventType,
        group: str,
        consumer: str,
        handler: Callable,
        count: int = 10,
        block_ms: int = 5000,
    ):
        stream_key = self._stream_key(event)

        try:
            await self._redis.xgroup_create(stream_key, group, id="0", mkstream=True)
        except Exception:
            pass

        logger.info(f"Consumer {consumer} escutando {event.value} no grupo {group}")

        while self._running:
            try:
                entries = await self._redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream_key: ">"},
                    count=count,
                    block=block_ms,
                )

                if not entries:
                    continue

                for _stream, messages in entries:
                    for msg_id, fields in messages:
                        message = Message(
                            id=fields.get("id", msg_id),
                            sender=fields.get("sender", ""),
                            content=fields.get("content", ""),
                            timestamp=fields.get("timestamp", ""),
                            payload=json.loads(fields.get("payload", "{}")),
                        )

                        try:
                            if asyncio.iscoroutinefunction(handler):
                                result = await handler(message)
                            else:
                                result = handler(message)

                            if result is not False:
                                await self.send_feedback(
                                    message.id,
                                    consumer,
                                    DeliveryStatus.ACK,
                                    "processado com sucesso",
                                )
                            else:
                                await self.send_feedback(
                                    message.id,
                                    consumer,
                                    DeliveryStatus.NACK,
                                    "handler retornou False",
                                )

                        except Exception as e:
                            await self.send_feedback(
                                message.id,
                                consumer,
                                DeliveryStatus.NACK,
                                str(e),
                            )
                            logger.error(f"Handler error: {e}")

                        await self._redis.xack(stream_key, group, msg_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(1)

    async def _audit_log(
        self, action: str, event: str, msg_id: str, sender: str, detail: str
    ):
        entry = {
            "action": action,
            "event": event,
            "message_id": msg_id,
            "sender": sender,
            "detail": detail,
            "timestamp": time.time(),
        }
        await self._redis.lpush(self.AUDIT_KEY, json.dumps(entry))
        await self._redis.ltrim(self.AUDIT_KEY, 0, 99999)

    async def get_audit_trail(
        self, msg_id: str = "", limit: int = 100
    ) -> list[dict]:
        entries = await self._redis.lrange(self.AUDIT_KEY, 0, limit - 1)
        result = [json.loads(e) for e in entries]
        if msg_id:
            result = [e for e in result if e.get("message_id") == msg_id]
        return result

    async def get_dlq(self, event: str = "", limit: int = 50) -> list[dict]:
        if event:
            entries = await self._redis.lrange(self._dlq_key(event), 0, limit - 1)
        else:
            entries = await self._redis.lrange(f"{self.DLQ_PREFIX}*", 0, limit - 1)
        return [json.loads(e) for e in entries]

    async def get_delivery_status(self, msg_id: str) -> dict | None:
        data = await self._redis.get(self._delivery_key(msg_id))
        return json.loads(data) if data else None

    async def get_feedback(self, msg_id: str) -> dict | None:
        data = await self._redis.get(self._feedback_key(msg_id))
        return json.loads(data) if data else None

    def start_consuming(self):
        self._running = True

    def stop_consuming(self):
        self._running = False


@lru_cache
def get_event_bus() -> EventBus:
    settings = get_settings()
    return EventBus(redis_url=settings.REDIS_URL)
