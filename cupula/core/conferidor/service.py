import json
import time
import asyncio
from enum import Enum
from typing import Any
from dataclasses import dataclass, field

import redis.asyncio as aioredis

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("conferidor")


class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class ValidationResult(Enum):
    VALID = "valid"
    INVALID_SCHEMA = "invalid_schema"
    DUPLICATE = "duplicate"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    UNKNOWN_SENDER = "unknown_sender"


@dataclass
class ValidationRule:
    name: str
    check: Any
    error_msg: str = ""


@dataclass
class RateLimitConfig:
    max_messages: int = 100
    window_seconds: int = 60


@dataclass
class ConferidorConfig:
    dedup_window_seconds: int = 300
    max_message_size_bytes: int = 1024 * 1024
    rate_limits: dict[str, RateLimitConfig] = field(default_factory=lambda: {
        "default": RateLimitConfig(max_messages=100, window_seconds=60),
        "heartbeat": RateLimitConfig(max_messages=30, window_seconds=60),
        "decision": RateLimitConfig(max_messages=20, window_seconds=60),
    })
    blocked_agents: set[str] = field(default_factory=set)
    priority_rules: dict[str, MessagePriority] = field(default_factory=lambda: {
        "decision.requested": MessagePriority.HIGH,
        "decision.failed": MessagePriority.CRITICAL,
        "agent.heartbeat": MessagePriority.LOW,
        "agent.registered": MessagePriority.NORMAL,
    })


class Conferidor:
    """Microserviço de validação, deduplicação e roteamento de mensagens.

    Responsabilidades:
    - Validar schema de todas as mensagens
    - Deduplicar mensagens repetidas
    - Rate limiting por agente e tipo
    - Atribuir prioridade às mensagens
    - Bloquear agentes problemáticos
    - Roteamento inteligente para shards
    """

    DEDUP_PREFIX = "cupula:dedup:"
    RATE_PREFIX = "cupula:rate:"
    QUEUE_PREFIX = "cupula:queue:"
    STATS_KEY = "cupula:conferidor:stats"

    def __init__(self, redis_url: str, config: ConferidorConfig | None = None):
        self.redis_url = redis_url
        self.config = config or ConferidorConfig()
        self._redis: aioredis.Redis | None = None
        self._validation_rules: list[ValidationRule] = []
        self._running = False
        self._stats = {
            "total_received": 0,
            "total_valid": 0,
            "total_rejected": 0,
            "total_duplicates": 0,
            "total_rate_limited": 0,
        }

        self._setup_default_rules()

    def _setup_default_rules(self):
        self._validation_rules = [
            ValidationRule(
                name="has_id",
                check=lambda m: bool(m.id),
                error_msg="mensagem sem ID",
            ),
            ValidationRule(
                name="has_sender",
                check=lambda m: bool(m.sender),
                error_msg="mensagem sem remetente",
            ),
            ValidationRule(
                name="has_event",
                check=lambda m: bool(m.event),
                error_msg="mensagem sem tipo de evento",
            ),
            ValidationRule(
                name="valid_event",
                check=lambda m: m.event in EventType,
                error_msg="tipo de evento desconhecido",
            ),
            ValidationRule(
                name="content_not_empty",
                check=lambda m: bool(m.content) or bool(m.payload),
                error_msg="mensagem vazia",
            ),
            ValidationRule(
                name="size_limit",
                check=lambda m: len(json.dumps(m.payload, ensure_ascii=False).encode()) < self.config.max_message_size_bytes,
                error_msg="mensagem excede tamanho maximo",
            ),
        ]

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=50,
        )
        await self._redis.ping()
        logger.info("Conferidor conectado ao Redis")

    async def disconnect(self):
        self._running = False
        if self._redis:
            await self._redis.close()

    def add_validation_rule(self, rule: ValidationRule):
        self._validation_rules.append(rule)

    def remove_validation_rule(self, name: str):
        self._validation_rules = [r for r in self._validation_rules if r.name != name]

    async def validate(self, message: Message) -> tuple[ValidationResult, str]:
        """Valida mensagem contra todas as regras."""
        self._stats["total_received"] += 1

        if message.sender in self.config.blocked_agents:
            self._stats["total_rejected"] += 1
            logger.warning(f"Agente bloqueado: {message.sender}")
            return ValidationResult.BLOCKED, "agente bloqueado"

        for rule in self._validation_rules:
            if not rule.check(message):
                self._stats["total_rejected"] += 1
                logger.warning(f"Validacao falhou [{rule.name}]: {rule.error_msg}")
                return ValidationResult.INVALID_SCHEMA, rule.error_msg

        is_dup = await self._check_duplicate(message)
        if is_dup:
            self._stats["total_duplicates"] += 1
            return ValidationResult.DUPLICATE, "mensagem duplicada"

        is_limited = await self._check_rate_limit(message)
        if is_limited:
            self._stats["total_rate_limited"] += 1
            return ValidationResult.RATE_LIMITED, "rate limit excedido"

        self._stats["total_valid"] += 1
        return ValidationResult.VALID, ""

    async def process(self, message: Message) -> dict[str, Any]:
        """Processa mensagem completa: valida + atribui prioridade + roteia."""
        result, error = await self.validate(message)

        if result != ValidationResult.VALID:
            return {
                "accepted": False,
                "validation": result.value,
                "error": error,
                "message_id": message.id,
            }

        priority = self._assign_priority(message)
        shard = self._determine_shard(message)

        await self._queue_message(message, priority, shard)

        return {
            "accepted": True,
            "validation": result.value,
            "priority": priority.name,
            "shard": shard,
            "message_id": message.id,
        }

    def _assign_priority(self, message: Message) -> MessagePriority:
        event_key = message.event.value if hasattr(message.event, "value") else str(message.event)

        if event_key in self.config.priority_rules:
            return self.config.priority_rules[event_key]

        custom_priority = message.payload.get("priority")
        if custom_priority is not None:
            try:
                return MessagePriority(int(custom_priority))
            except (ValueError, IndexError):
                pass

        return MessagePriority.NORMAL

    def _determine_shard(self, message: Message) -> str:
        event_val = message.event.value if hasattr(message.event, "value") else str(message.event)

        if event_val.startswith("agent."):
            return "agents"

        if event_val.startswith("decision."):
            role = message.payload.get("role", "general")
            return f"decisions:{role}"

        if event_val.startswith("sandbox."):
            return "sandbox"

        if event_val.startswith("team."):
            return "teams"

        return "general"

    async def _check_duplicate(self, message: Message) -> bool:
        dedup_key = f"{self.DEDUP_PREFIX}{message.id}"

        exists = await self._redis.exists(dedup_key)
        if exists:
            return True

        await self._redis.setex(
            dedup_key,
            self.config.dedup_window_seconds,
            "1",
        )
        return False

    async def _check_rate_limit(self, message: Message) -> bool:
        event_key = message.event.value if hasattr(message.event, "value") else "default"

        for pattern, config in self.config.rate_limits.items():
            if pattern in event_key or pattern == "default":
                rate_key = f"{self.RATE_PREFIX}{message.sender}:{pattern}"

                current = await self._redis.incr(rate_key)
                if current == 1:
                    await self._redis.expire(rate_key, config.window_seconds)

                if current > config.max_messages:
                    logger.warning(
                        f"Rate limit atingido: {message.sender} "
                        f"({current}/{config.max_messages} em {config.window_seconds}s)"
                    )
                    return True

                return False

        return False

    async def _queue_message(
        self, message: Message, priority: MessagePriority, shard: str
    ):
        queue_key = f"{self.QUEUE_PREFIX}{shard}"

        entry = {
            "message_id": message.id,
            "sender": message.sender,
            "event": message.event.value if hasattr(message.event, "value") else str(message.event),
            "content": message.content,
            "timestamp": message.timestamp,
            "payload": json.dumps(message.payload, ensure_ascii=False),
            "priority": priority.value,
            "shard": shard,
            "conferidor_timestamp": time.time(),
        }

        await self._redis.lpush(queue_key, json.dumps(entry))
        await self._redis.ltrim(queue_key, 0, 9999)

        stats_key = f"{self.STATS_KEY}:{shard}"
        await self._redis.hincrby(stats_key, "queued", 1)
        await self._redis.hincrby(stats_key, f"priority:{priority.name}", 1)

        logger.debug(f"Enfileirado [{priority.name}] -> {shard}: {message.id}")

    async def get_stats(self) -> dict:
        return {
            **self._stats,
            "acceptance_rate": (
                self._stats["total_valid"] / max(self._stats["total_received"], 1)
            ),
            "rejection_rate": (
                self._stats["total_rejected"] / max(self._stats["total_received"], 1)
            ),
            "duplicate_rate": (
                self._stats["total_duplicates"] / max(self._stats["total_received"], 1)
            ),
        }

    async def block_agent(self, agent_id: str, reason: str = ""):
        self.config.blocked_agents.add(agent_id)
        logger.warning(f"Agente bloqueado: {agent_id} ({reason})")

    async def unblock_agent(self, agent_id: str):
        self.config.blocked_agents.discard(agent_id)
        logger.info(f"Agente desbloqueado: {agent_id}")

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
