import json
import time
import asyncio
from typing import Any

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.core.message import (
    Message,
    DecisionRequest,
    DecisionResponse,
    EventType,
    AgentRole,
)
from cupula.core.bus.event_bus import EventBus, DeliveryStatus
from cupula.core.conferidor.service import Conferidor
from cupula.core.reputation.service import ReputationService
from cupula.core.circuit_breaker.service import CircuitBreaker
from cupula.core.metrics.service import MetricsService
from cupula.core.batch.service import BatchService

logger = get_logger("orchestrator")


class Orchestrator:
    """Orquestrador central que gerencia todo o ciclo de decisão.

    Coordena:
    - EventBus para comunicação
    - Conferidor para validação
    - Reputação para pesos
    - Circuit Breaker para proteção
    - Métricas para observabilidade
    - Batch para performance
    """

    def __init__(self):
        settings = get_settings()

        self.bus = EventBus(redis_url=settings.REDIS_URL)
        self.conferidor = Conferidor(redis_url=settings.REDIS_URL)
        self.reputation = ReputationService(redis_url=settings.REDIS_URL)
        self.circuit_breaker = CircuitBreaker(redis_url=settings.REDIS_URL)
        self.metrics = MetricsService(redis_url=settings.REDIS_URL)
        self.batch = BatchService(redis_url=settings.REDIS_URL)

        self._agents: dict[str, Any] = {}
        self._running = False

    async def start(self):
        """Inicializa todos os componentes."""
        logger.info("Iniciando Orchestrator...")

        await self.bus.connect()
        await self.conferidor.connect()
        await self.reputation.connect()
        await self.circuit_breaker.connect()
        await self.metrics.connect()
        await self.batch.connect()

        self.bus.start_consuming()
        self.conferidor.start()
        await self.batch.start_auto_flush()

        self._running = True

        await self.metrics.increment("orchestrator.startups")

        logger.info("Orchestrator iniciado com sucesso")

    async def stop(self):
        """Para todos os componentes."""
        logger.info("Parando Orchestrator...")
        self._running = False

        self.bus.stop_consuming()
        self.conferidor.stop()
        await self.batch.flush()

        await self.bus.disconnect()
        await self.conferidor.disconnect()
        await self.reputation.disconnect()
        await self.circuit_breaker.disconnect()
        await self.metrics.disconnect()
        await self.batch.disconnect()

        logger.info("Orchestrator parado")

    async def submit_decision(self, request: DecisionRequest) -> dict[str, Any]:
        """Submete uma decisão para processamento pela cúpula."""
        start_time = time.time()

        logger.info(f"Decisão submetida: [{request.id}] {request.title}")

        message = Message(
            id=request.id,
            event=EventType.DECISION_REQUESTED,
            sender="orchestrator",
            content=request.description,
            payload={
                "title": request.title,
                "description": request.description,
                "context": request.context,
                "constraints": request.constraints,
                "priority": request.priority,
            },
        )

        validation = await self.conferidor.process(message)

        if not validation["accepted"]:
            logger.warning(f"Decisão rejeitada pelo Conferidor: {validation['error']}")
            return {
                "status": "rejected",
                "reason": validation["error"],
                "validation": validation,
            }

        await self.metrics.increment("decisions.submitted")

        target_agents = self._select_agents(request)

        responses = []
        for agent_id in target_agents:
            can_run = await self.circuit_breaker.can_execute(agent_id)
            if not can_run:
                logger.warning(f"Agente {agent_id} bloqueado por Circuit Breaker")
                await self.metrics.increment("decisions.skipped_circuit_breaker")
                continue

            response = await self._process_agent_decision(agent_id, request)
            if response:
                responses.append(response)

        result = await self._synthesize_decision(request, responses)

        elapsed_ms = (time.time() - start_time) * 1000
        await self.metrics.record_timing("decision_total", elapsed_ms)

        await self.bus.publish(
            EventType.DECISION_COMPLETED,
            Message(
                event=EventType.DECISION_COMPLETED,
                sender="orchestrator",
                content=f"Decisão {request.id} completada",
                payload={
                    "request_id": request.id,
                    "verdict": result.get("verdict", ""),
                    "elapsed_ms": elapsed_ms,
                },
            ),
        )

        await self.batch.add("metrics", {
            "name": "decision_completed",
            "value": elapsed_ms,
            "tags": {"verdict": result.get("verdict", "unknown")},
        })

        return result

    def _select_agents(self, request: DecisionRequest) -> list[str]:
        if request.required_roles:
            return [
                aid for aid, agent in self._agents.items()
                if agent.get("role") in request.required_roles
            ]

        return [
            aid for aid, agent in self._agents.items()
            if agent.get("status") == "idle"
        ][:10]

    async def _process_agent_decision(
        self, agent_id: str, request: DecisionRequest
    ) -> dict | None:
        start = time.time()

        try:
            agent = self._agents.get(agent_id)
            if not agent:
                return None

            await self.bus.publish(
                EventType.DECISION_ANALYZING,
                Message(
                    event=EventType.DECISION_ANALYZING,
                    sender=agent_id,
                    content=f"Analisando decisão {request.id}",
                    payload={"request_id": request.id},
                ),
            )

            await self.batch.add_heartbeat(agent_id, "busy")

            response = await agent["instance"].analyze(request)

            elapsed_ms = (time.time() - start) * 1000

            await self.reputation.update_score(
                agent_id,
                success=True,
                response_time_ms=elapsed_ms,
                confidence=response.confidence if hasattr(response, "confidence") else 0.5,
            )

            await self.circuit_breaker.record_success(agent_id)
            await self.metrics.record_timing("agent_response", elapsed_ms)

            await self.bus.send_feedback(
                request.id,
                agent_id,
                DeliveryStatus.ACK,
                "análise concluída",
            )

            return {
                "agent_id": agent_id,
                "verdict": response.verdict,
                "reasoning": response.reasoning,
                "risks": response.risks,
                "recommendations": response.recommendations,
                "confidence": response.confidence,
                "response_time_ms": elapsed_ms,
            }

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000

            await self.reputation.update_score(
                agent_id, success=False, response_time_ms=elapsed_ms
            )
            await self.circuit_breaker.record_failure(agent_id, str(e))
            await self.metrics.increment("agent.failures")

            await self.bus.send_feedback(
                request.id,
                agent_id,
                DeliveryStatus.NACK,
                str(e),
            )

            logger.error(f"Erro no agente {agent_id}: {e}")
            return None

    async def _synthesize_decision(
        self, request: DecisionRequest, responses: list[dict]
    ) -> dict[str, Any]:
        if not responses:
            return {
                "status": "no_responses",
                "verdict": "REVISAO",
                "reasoning": "Nenhum agente respondeu",
            }

        verdicts = [r["verdict"] for r in responses]

        weights = []
        for r in responses:
            weight = await self.reputation.get_weight(r["agent_id"])
            weights.append(weight)

        weighted_verdicts = {}
        for verdict, weight in zip(verdicts, weights):
            weighted_verdicts[verdict] = weighted_verdicts.get(verdict, 0) + weight

        final_verdict = max(weighted_verdicts, key=weighted_verdicts.get)

        all_risks = []
        all_recs = []
        for r in responses:
            all_risks.extend(r.get("risks", []))
            all_recs.extend(r.get("recommendations", []))

        avg_confidence = sum(r.get("confidence", 0.5) for r in responses) / len(responses)

        synthesis = {
            "request_id": request.id,
            "title": request.title,
            "verdict": final_verdict,
            "confidence": avg_confidence,
            "responses_count": len(responses),
            "agent_responses": responses,
            "risks": list(set(all_risks)),
            "recommendations": list(set(all_recs)),
            "weighted_verdicts": weighted_verdicts,
        }

        logger.info(
            f"Decisão sintetizada: [{final_verdict}] "
            f"confiança={avg_confidence:.2f} "
            f"agentes={len(responses)}"
        )

        return synthesis

    def register_agent(self, agent_id: str, instance: Any, role: str = "custom"):
        self._agents[agent_id] = {
            "instance": instance,
            "role": role,
            "status": "idle",
            "registered_at": time.time(),
        }
        logger.info(f"Agente registrado: {agent_id} (role={role})")

    async def unregister_agent(self, agent_id: str):
        self._agents.pop(agent_id, None)
        await self.circuit_breaker.force_close(agent_id)
        logger.info(f"Agente removido: {agent_id}")

    async def get_system_status(self) -> dict:
        return {
            "running": self._running,
            "agents_registered": len(self._agents),
            "agents": {
                aid: {"role": a["role"], "status": a["status"]}
                for aid, a in self._agents.items()
            },
            "conferidor": await self.conferidor.get_stats(),
            "metrics": await self.metrics.get_health(),
            "circuit_breakers": await self.circuit_breaker.get_all_status(),
            "reputation_leaderboard": await self.reputation.get_leaderboard(10),
        }
