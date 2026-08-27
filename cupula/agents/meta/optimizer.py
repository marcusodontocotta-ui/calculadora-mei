import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("meta.optimizer")


class OptimizerAgent:
    """Meta-agente que otimiza performance do sistema.

    Responsabilidades:
    - Analisar throughput e latência
    - Sugerir ajustes de batch size e flush interval
    - Balancear carga entre agentes
    - Otimizar uso de Redis (memória, conexões)
    - Recomendar escalabilidade (horizontal/vertical)
    """

    def __init__(self):
        self.agent_id = "meta-optimizer"
        self.optimization_history: list[dict] = []
        self.baseline_metrics: dict = {}

    async def analyze_performance(
        self,
        metrics: dict,
        batch_stats: dict,
        conferidor_stats: dict,
    ) -> dict[str, Any]:
        """Analisa performance e gera recomendações de otimização."""
        optimizations = []

        optimizations.extend(self._optimize_batch(metrics, batch_stats))
        optimizations.extend(self._optimize_redis(metrics))
        optimizations.extend(self._optimize_scaling(metrics))
        optimizations.extend(self._optimize_conferidor(conferidor_stats))

        result = {
            "timestamp": time.time(),
            "total_optimizations": len(optimizations),
            "optimizations": optimizations,
            "estimated_improvement": self._estimate_improvement(optimizations),
        }

        self.optimization_history.append(result)
        if len(self.optimization_history) > 50:
            self.optimization_history = self.optimization_history[-25:]

        logger.info(f"Análise de performance: {len(optimizations)} otimizações sugeridas")

        return result

    def _optimize_batch(self, metrics: dict, batch_stats: dict) -> list[dict]:
        opts = []

        buffer_sizes = batch_stats.get("buffer_sizes", {})
        total_buffered = sum(buffer_sizes.values())

        if total_buffered > 100:
            opts.append({
                "type": "batch_flush",
                "current": batch_stats.get("config", {}).get("flush_interval", 2),
                "suggested": 1.0,
                "reason": f"Buffer acumulando ({total_buffered} items)",
                "impact": "low",
            })

        if total_buffered == 0 and batch_stats.get("total_processed", 0) > 1000:
            opts.append({
                "type": "batch_size",
                "current": batch_stats.get("config", {}).get("max_size", 50),
                "suggested": 100,
                "reason": "Sistema maduro, pode agrupar mais",
                "impact": "low",
            })

        return opts

    def _optimize_redis(self, metrics: dict) -> list[dict]:
        opts = []

        active_agents = metrics.get("active_agents", {}).get("count", 0)

        if active_agents > 500:
            opts.append({
                "type": "redis_connections",
                "current": 50,
                "suggested": min(200, active_agents // 5),
                "reason": f"Muitos agentes ativos ({active_agents})",
                "impact": "medium",
            })

        return opts

    def _optimize_scaling(self, metrics: dict) -> list[dict]:
        opts = []

        health = metrics.get("health", {})
        latency = metrics.get("latency_decision", {})

        p95 = latency.get("p95", 0)

        if p95 > 3000:
            opts.append({
                "type": "scale_workers",
                "current": 1,
                "suggested": 3,
                "reason": f"Latência P95 alta ({p95:.0f}ms)",
                "impact": "high",
            })

        if health.get("score", 1) < 0.5:
            opts.append({
                "type": "scale_agents",
                "current": health.get("active_agents", 0),
                "suggested": "investigate",
                "reason": "Sistema degradado, primeiro resolver causas",
                "impact": "high",
            })

        return opts

    def _optimize_conferidor(self, stats: dict) -> list[dict]:
        opts = []

        dup_rate = stats.get("duplicate_rate", 0)
        if dup_rate > 0.05:
            opts.append({
                "type": "dedup_window",
                "current": 300,
                "suggested": 120,
                "reason": f"Taxa de duplicatas alta ({dup_rate:.1%})",
                "impact": "low",
            })

        return opts

    def _estimate_improvement(self, optimizations: list[dict]) -> dict:
        impact_counts = {"high": 0, "medium": 0, "low": 0}
        for opt in optimizations:
            impact = opt.get("impact", "low")
            impact_counts[impact] = impact_counts.get(impact, 0) + 1

        score = 0
        score += impact_counts["high"] * 0.15
        score += impact_counts["medium"] * 0.08
        score += impact_counts["low"] * 0.03

        return {
            "potential_improvement": min(0.5, score),
            "high_impact_count": impact_counts["high"],
            "medium_impact_count": impact_counts["medium"],
            "low_impact_count": impact_counts["low"],
        }

    async def handle_message(self, message: Message) -> dict | None:
        if message.event == EventType.DECISION_COMPLETED:
            return await self._on_decision(message)
        return None

    async def _on_decision(self, message: Message) -> dict:
        payload = message.payload
        if payload.get("verdict") == "CONDICIONAL":
            return {
                "action": "log_conditional",
                "suggestion": "Decisões condicionais podem indicar gargalos",
            }
        return {"action": "none"}
