import json
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

import redis.asyncio as aioredis

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("batch")


@dataclass
class BatchConfig:
    max_size: int = 50
    flush_interval_seconds: float = 2.0
    buffer_ttl_seconds: int = 10


class BatchService:
    """Serviço de agrupamento de mensagens para alta performance.

    Útil para:
    - Heartbeats de milhares de agentes
    - Métricas de alta frequência
    - Sinais destatus em lote
    - Updates de reputação em batch

    Agrupa mensagens e processa em lote, reduzindo round trips no Redis.
    """

    BATCH_PREFIX = "cupula:batch:"
    PROCESSED_KEY = "cupula:batch:processed"

    def __init__(self, redis_url: str, config: BatchConfig | None = None):
        self.redis_url = redis_url
        self.config = config or BatchConfig()
        self._redis: aioredis.Redis | None = None
        self._buffers: dict[str, list[dict]] = {}
        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._flush_task: asyncio.Task | None = None

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        await self._redis.ping()
        logger.info("BatchService conectado")

    async def disconnect(self):
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        if self._redis:
            await self._redis.close()

    def register_handler(self, batch_type: str, handler: Callable):
        self._handlers[batch_type] = handler

    async def add(self, batch_type: str, item: dict[str, Any]):
        if batch_type not in self._buffers:
            self._buffers[batch_type] = []

        item["_batch_timestamp"] = time.time()
        self._buffers[batch_type].append(item)

        if len(self._buffers[batch_type]) >= self.config.max_size:
            await self.flush(batch_type)

    async def add_heartbeat(self, agent_id: str, status: str = "alive", load: float = 0.0):
        await self.add("heartbeats", {
            "agent_id": agent_id,
            "status": status,
            "load": load,
        })

    async def add_metric(self, name: str, value: float, tags: dict[str, str] | None = None):
        await self.add("metrics", {
            "name": name,
            "value": value,
            "tags": tags or {},
        })

    async def add_reputation_update(self, agent_id: str, success: bool, response_time_ms: float):
        await self.add("reputation", {
            "agent_id": agent_id,
            "success": success,
            "response_time_ms": response_time_ms,
        })

    async def flush(self, batch_type: str | None = None):
        types_to_flush = [batch_type] if batch_type else list(self._buffers.keys())

        for bt in types_to_flush:
            items = self._buffers.get(bt, [])
            if not items:
                continue

            batch = items.copy()
            self._buffers[bt] = []

            batch_key = f"{self.BATCH_PREFIX}{bt}"
            await self._redis.rpush(batch_key, json.dumps(batch, ensure_ascii=False))
            await self._redis.ltrim(batch_key, 0, 999)

            await self._redis.incrby(self.PROCESSED_KEY, len(batch))

            handler = self._handlers.get(bt)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(batch)
                    else:
                        handler(batch)
                except Exception as e:
                    logger.error(f"Handler de batch {bt} falhou: {e}")
            else:
                logger.debug(f"Batch {bt}: {len(batch)} items processados (sem handler)")

    async def start_auto_flush(self):
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"Auto-flush iniciado (intervalo: {self.config.flush_interval_seconds}s)")

    async def _flush_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")

    async def get_stats(self) -> dict:
        total_processed = await self._redis.get(self.PROCESSED_KEY) or 0

        buffer_sizes = {}
        for bt, items in self._buffers.items():
            buffer_sizes[bt] = len(items)

        return {
            "total_processed": int(total_processed),
            "buffer_sizes": buffer_sizes,
            "config": {
                "max_size": self.config.max_size,
                "flush_interval": self.config.flush_interval_seconds,
            },
        }

    async def process_pending(self, batch_type: str, limit: int = 100) -> list[dict]:
        batch_key = f"{self.BATCH_PREFIX}{batch_type}"
        items = await self._redis.lrange(batch_key, 0, limit - 1)

        if items:
            await self._redis.ltrim(batch_key, limit, -1)

        return [json.loads(item) for item in items]
