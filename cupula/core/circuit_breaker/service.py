import json
import time
from enum import Enum
from dataclasses import dataclass, field

import redis.asyncio as aioredis

from cupula.core.logger import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class AgentCircuit:
    agent_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    total_trips: int = 0


class CircuitBreaker:
    """Circuit Breaker distribuido por agente.

    Estados:
    - CLOSED: normal, mensagens passam
    - OPEN: agente problemático, mensagens bloqueadas
    - HALF_OPEN: testando se agente voltou ao normal

    Transições:
    - CLOSED -> OPEN: falhas >= threshold
    - OPEN -> HALF_OPEN: timeout do periodo de cooldown
    - HALF_OPEN -> CLOSED: sucesso no teste
    - HALF_OPEN -> OPEN: falha no teste
    """

    CIRCUIT_PREFIX = "cupula:circuit:"
    STATS_KEY = "cupula:circuit:stats"

    def __init__(
        self,
        redis_url: str,
        failure_threshold: int = 5,
        cooldown_seconds: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        self._circuits: dict[str, AgentCircuit] = {}

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=30,
        )
        await self._redis.ping()
        logger.info("CircuitBreaker conectado")

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    async def can_execute(self, agent_id: str) -> bool:
        circuit = await self._get_circuit(agent_id)

        if circuit.state == CircuitState.CLOSED:
            return True

        if circuit.state == CircuitState.OPEN:
            elapsed = time.time() - circuit.last_failure_time
            if elapsed >= self.cooldown_seconds:
                await self._transition(agent_id, circuit, CircuitState.HALF_OPEN)
                return True
            return False

        if circuit.state == CircuitState.HALF_OPEN:
            return circuit.success_count < self.half_open_max_calls

        return False

    async def record_success(self, agent_id: str):
        circuit = await self._get_circuit(agent_id)

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1
            if circuit.success_count >= self.half_open_max_calls:
                await self._transition(agent_id, circuit, CircuitState.CLOSED)
                circuit.failure_count = 0
                circuit.success_count = 0
                logger.info(f"Circuit FECHADO para {agent_id} (recuperado)")

        elif circuit.state == CircuitState.CLOSED:
            circuit.failure_count = max(0, circuit.failure_count - 1)

        await self._save_circuit(circuit)

    async def record_failure(self, agent_id: str, reason: str = ""):
        circuit = await self._get_circuit(agent_id)
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            await self._transition(agent_id, circuit, CircuitState.OPEN)
            circuit.total_trips += 1
            logger.warning(
                f"Circuit REABERTO para {agent_id}: falha no teste ({reason})"
            )

        elif circuit.state == CircuitState.CLOSED:
            if circuit.failure_count >= self.failure_threshold:
                await self._transition(agent_id, circuit, CircuitState.OPEN)
                circuit.total_trips += 1
                logger.warning(
                    f"Circuit ABERTO para {agent_id}: {circuit.failure_count} "
                    f"falhas consecutivas ({reason})"
                )

        await self._save_circuit(circuit)

        await self._redis.hincrby(self.STATS_KEY, "total_failures", 1)
        await self._redis.hincrby(self.STATS_KEY, f"failures:{agent_id}", 1)

    async def _get_circuit(self, agent_id: str) -> AgentCircuit:
        if agent_id in self._circuits:
            return self._circuits[agent_id]

        data = await self._redis.get(f"{self.CIRCUIT_PREFIX}{agent_id}")
        if data:
            d = json.loads(data)
            circuit = AgentCircuit(
                agent_id=agent_id,
                state=CircuitState(d["state"]),
                failure_count=d.get("failure_count", 0),
                success_count=d.get("success_count", 0),
                last_failure_time=d.get("last_failure_time", 0),
                last_state_change=d.get("last_state_change", time.time()),
                total_trips=d.get("total_trips", 0),
            )
        else:
            circuit = AgentCircuit(agent_id=agent_id)

        self._circuits[agent_id] = circuit
        return circuit

    async def _transition(
        self, agent_id: str, circuit: AgentCircuit, new_state: CircuitState
    ):
        old_state = circuit.state
        circuit.state = new_state
        circuit.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            circuit.failure_count = 0
            circuit.success_count = 0

        if new_state == CircuitState.HALF_OPEN:
            circuit.success_count = 0

        await self._redis.hincrby(
            self.STATS_KEY, f"transitions:{old_state.value}->{new_state.value}", 1
        )

        logger.info(
            f"Circuit {agent_id}: {old_state.value} -> {new_state.value}"
        )

    async def _save_circuit(self, circuit: AgentCircuit):
        data = json.dumps({
            "agent_id": circuit.agent_id,
            "state": circuit.state.value,
            "failure_count": circuit.failure_count,
            "success_count": circuit.success_count,
            "last_failure_time": circuit.last_failure_time,
            "last_state_change": circuit.last_state_change,
            "total_trips": circuit.total_trips,
        })
        ttl = self.cooldown_seconds * 3
        await self._redis.setex(f"{self.CIRCUIT_PREFIX}{circuit.agent_id}", ttl, data)

    async def get_status(self, agent_id: str) -> dict:
        circuit = await self._get_circuit(agent_id)
        return {
            "agent_id": agent_id,
            "state": circuit.state.value,
            "failure_count": circuit.failure_count,
            "total_trips": circuit.total_trips,
            "can_execute": await self.can_execute(agent_id),
        }

    async def get_all_status(self) -> list[dict]:
        keys = []
        async for key in self._redis.scan_iter(f"{self.CIRCUIT_PREFIX}*"):
            keys.append(key)

        statuses = []
        for key in keys:
            data = await self._redis.get(key)
            if data:
                statuses.append(json.loads(data))

        return statuses

    async def force_open(self, agent_id: str):
        circuit = await self._get_circuit(agent_id)
        await self._transition(agent_id, circuit, CircuitState.OPEN)
        circuit.total_trips += 1
        await self._save_circuit(circuit)
        logger.warning(f"Circuit FORÇADO ABERTO para {agent_id}")

    async def force_close(self, agent_id: str):
        circuit = await self._get_circuit(agent_id)
        await self._transition(agent_id, circuit, CircuitState.CLOSED)
        await self._save_circuit(circuit)
        logger.info(f"Circuit FECHADO manualmente para {agent_id}")

    async def reset(self, agent_id: str):
        circuit = AgentCircuit(agent_id=agent_id)
        self._circuits[agent_id] = circuit
        await self._redis.delete(f"{self.CIRCUIT_PREFIX}{agent_id}")
        logger.info(f"Circuit RESETADO para {agent_id}")
