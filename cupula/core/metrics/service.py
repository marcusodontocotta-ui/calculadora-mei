import json
import time
from typing import Any
from collections import defaultdict

import redis.asyncio as aioredis

from cupula.core.logger import get_logger

logger = get_logger("metrics")


class MetricsService:
    """Serviço de métricas e observabilidade em tempo real.

    Coleta e expõe:
    - Throughput (mensagens/segundo)
    - Latência (p50, p95, p99)
    - Taxa de ACK/NACK
    - Agentes ativos
    - Uso de recursos por agente
    - Health geral do sistema
    """

    METRICS_PREFIX = "cupula:metrics:"
    SNAPSHOTS_KEY = "cupula:metrics:snapshots"
    HEALTH_KEY = "cupula:metrics:health"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        await self._redis.ping()
        logger.info("MetricsService conectado")

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    async def increment(self, name: str, value: int = 1, tags: dict[str, str] | None = None):
        key = f"{self.METRICS_PREFIX}{name}"
        await self._redis.incrby(key, value)

        tag_key = key
        if tags:
            tag_suffix = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
            tag_key = f"{key}:{tag_suffix}"
            await self._redis.incrby(tag_key, value)

        self._counters[name] += value

    async def record_timing(self, name: str, duration_ms: float, tags: dict[str, str] | None = None):
        key = f"{self.METRICS_PREFIX}timing:{name}"
        await self._redis.lpush(key, json.dumps({
            "value": duration_ms,
            "timestamp": time.time(),
        }))
        await self._redis.ltrim(key, 0, 999)

        self._timers[name].append(duration_ms)
        if len(self._timers[name]) > 1000:
            self._timers[name] = self._timers[name][-500:]

    async def set_gauge(self, name: str, value: float):
        key = f"{self.METRICS_PREFIX}gauge:{name}"
        await self._redis.set(key, json.dumps({
            "value": value,
            "timestamp": time.time(),
        }))
        self._gauges[name] = value

    async def record_agent_active(self, agent_id: str):
        key = f"{self.METRICS_PREFIX}agents:active"
        await self._redis.sadd(key, agent_id)
        await self._redis.expire(key, 120)

    async def record_agent_inactive(self, agent_id: str):
        key = f"{self.METRICS_PREFIX}agents:active"
        await self._redis.srem(key, agent_id)

    async def get_throughput(self, window_seconds: int = 60) -> dict:
        counters_snapshot = {}
        async for key in self._redis.scan_iter(f"{self.METRICS_PREFIX}*"):
            if "timing:" in key or "gauge:" in key or "agents:" in key or "snapshots" in key or "health" in key:
                continue
            val = await self._redis.get(key)
            if val:
                name = key.replace(self.METRICS_PREFIX, "")
                counters_snapshot[name] = int(val)

        return {
            "window_seconds": window_seconds,
            "counters": counters_snapshot,
        }

    async def get_latency(self, name: str) -> dict:
        key = f"{self.METRICS_PREFIX}timing:{name}"
        entries = await self._redis.lrange(key, 0, -1)

        if not entries:
            return {"name": name, "count": 0}

        values = sorted([json.loads(e)["value"] for e in entries])
        count = len(values)

        return {
            "name": name,
            "count": count,
            "min": values[0],
            "max": values[-1],
            "avg": sum(values) / count,
            "p50": values[count // 2],
            "p95": values[int(count * 0.95)] if count > 20 else values[-1],
            "p99": values[int(count * 0.99)] if count > 100 else values[-1],
        }

    async def get_active_agents(self) -> dict:
        key = f"{self.METRICS_PREFIX}agents:active"
        agents = await self._redis.smembers(key)
        return {
            "count": len(agents),
            "agents": list(agents),
        }

    async def get_gauges(self) -> dict:
        gauges = {}
        async for key in self._redis.scan_iter(f"{self.METRICS_PREFIX}gauge:*"):
            name = key.replace(f"{self.METRICS_PREFIX}gauge:", "")
            data = await self._redis.get(key)
            if data:
                gauges[name] = json.loads(data)
        return gauges

    async def snapshot(self):
        """Tira snapshot completo das métricas para análise histórica."""
        active = await self.get_active_agents()
        gauges = await self.get_gauges()

        snapshot_data = {
            "timestamp": time.time(),
            "active_agents": active["count"],
            "gauges": gauges,
            "counters": dict(self._counters),
        }

        await self._redis.lpush(self.SNAPSHOTS_KEY, json.dumps(snapshot_data))
        await self._redis.ltrim(self.SNAPSHOTS_KEY, 0, 999)

        return snapshot_data

    async def get_health(self) -> dict:
        active = await self.get_active_agents()
        gauges = await self.get_gauges()

        health_score = 1.0
        issues = []

        if active["count"] == 0:
            health_score -= 0.5
            issues.append("nenhum agente ativo")

        circuit_open = gauges.get("circuits_open", {}).get("value", 0)
        if circuit_open > 0:
            health_score -= 0.1 * circuit_open
            issues.append(f"{int(circuit_open)} circuit breaker(es) aberto(s)")

        nack_rate = gauges.get("nack_rate", {}).get("value", 0)
        if nack_rate > 0.3:
            health_score -= 0.3
            issues.append(f"taxa de NACK alta: {nack_rate:.1%}")

        health_score = max(0.0, min(1.0, health_score))

        status = "healthy" if health_score > 0.7 else "degraded" if health_score > 0.3 else "critical"

        return {
            "status": status,
            "score": round(health_score, 3),
            "active_agents": active["count"],
            "issues": issues,
            "timestamp": time.time(),
        }

    async def get_dashboard(self) -> dict:
        return {
            "health": await self.get_health(),
            "throughput": await self.get_throughput(),
            "active_agents": await self.get_active_agents(),
            "gauges": await self.get_gauges(),
            "latency_decision": await self.get_latency("decision_total"),
            "latency_agent": await self.get_latency("agent_response"),
        }
