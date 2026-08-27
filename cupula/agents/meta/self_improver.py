import json
import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("meta.self_improver")


class SelfImproverAgent:
    """Meta-agente que analisa o sistema e sugere melhorias.

    Responsabilidades:
    - Monitorar performance dos agentes
    - Identificar gargalos e ineficiências
    - Sugerir ajustes de parâmetros
    - Propor novas regras de validação
    - Recomendar mudanças de arquitetura
    """

    def __init__(self):
        self.agent_id = "meta-self-improver"
        self.analysis_history: list[dict] = []
        self.improvement_suggestions: list[dict] = []

    async def analyze_system(
        self,
        metrics: dict,
        reputation_data: list[dict],
        circuit_data: list[dict],
        conferidor_stats: dict,
    ) -> dict[str, Any]:
        """Analisa estado completo do sistema e gera sugestões."""
        suggestions = []

        suggestions.extend(self._analyze_metrics(metrics))
        suggestions.extend(self._analyze_reputation(reputation_data))
        suggestions.extend(self._analyze_circuits(circuit_data))
        suggestions.extend(self._analyze_conferidor(conferidor_stats))

        severity_counts = {
            "critical": len([s for s in suggestions if s["severity"] == "critical"]),
            "high": len([s for s in suggestions if s["severity"] == "high"]),
            "medium": len([s for s in suggestions if s["severity"] == "medium"]),
            "low": len([s for s in suggestions if s["severity"] == "low"]),
        }

        analysis = {
            "timestamp": time.time(),
            "total_suggestions": len(suggestions),
            "severity_counts": severity_counts,
            "suggestions": suggestions,
            "system_health_score": self._calculate_health_score(
                metrics, reputation_data, circuit_data
            ),
        }

        self.analysis_history.append(analysis)
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-50:]

        logger.info(
            f"Análise completa: {len(suggestions)} sugestões "
            f"({severity_counts['critical']} críticas)"
        )

        return analysis

    def _analyze_metrics(self, metrics: dict) -> list[dict]:
        suggestions = []

        health = metrics.get("health", {})
        if health.get("score", 1.0) < 0.5:
            suggestions.append({
                "type": "health_critical",
                "severity": "critical",
                "title": "Saúde do sistema comprometida",
                "description": f"Score de saúde: {health.get('score', 0):.2f}",
                "action": "Investigar agentes com falhas e circuit breakers abertos",
                "estimated_impact": "high",
            })

        active = metrics.get("active_agents", {})
        if active.get("count", 0) == 0:
            suggestions.append({
                "type": "no_agents",
                "severity": "critical",
                "title": "Nenhum agente ativo",
                "description": "Sistema sem agentes processando",
                "action": "Verificar conectividade e reiniciar agentes necessários",
                "estimated_impact": "high",
            })

        latency = metrics.get("latency_decision", {})
        if latency.get("p95", 0) > 5000:
            suggestions.append({
                "type": "high_latency",
                "severity": "high",
                "title": "Latência alta nas decisões",
                "description": f"P95: {latency.get('p95', 0):.0f}ms",
                "action": "Considerar mais workers ou reduzir complexidade dos agentes",
                "estimated_impact": "medium",
            })

        return suggestions

    def _analyze_reputation(self, reputation_data: list[dict]) -> list[dict]:
        suggestions = []

        low_score_agents = [
            a for a in reputation_data
            if a.get("overall_score", 1.0) < 0.3 and a.get("total_tasks", 0) > 10
        ]

        if low_score_agents:
            suggestions.append({
                "type": "low_reputation",
                "severity": "high",
                "title": f"{len(low_score_agents)} agentes com reputação baixa",
                "description": "Agentes: " + ", ".join(
                    a["agent_id"] for a in low_score_agents[:5]
                ),
                "action": "Revisar lógica desses agentes ou reduzir seu peso nas decisões",
                "estimated_impact": "medium",
            })

        high_nack = [
            a for a in reputation_data
            if a.get("nack_count", 0) > a.get("total_tasks", 0) * 0.3
        ]

        if high_nack:
            suggestions.append({
                "type": "high_nack_rate",
                "severity": "medium",
                "title": "Alta taxa de rejeição",
                "description": f"{len(high_nack)} agentes com NACK > 30%",
                "action": "Verificar se agentes estão recebendo mensagens adequadas",
                "estimated_impact": "medium",
            })

        return suggestions

    def _analyze_circuits(self, circuit_data: list[dict]) -> list[dict]:
        suggestions = []

        open_circuits = [
            c for c in circuit_data
            if c.get("state") == "open"
        ]

        if open_circuits:
            suggestions.append({
                "type": "open_circuits",
                "severity": "high",
                "title": f"{len(open_circuits)} circuit breakers abertos",
                "description": "Agentes bloqueados: " + ", ".join(
                    c.get("agent_id", "?") for c in open_circuits[:5]
                ),
                "action": "Investigar causa raiz das falhas e considerar restart do agente",
                "estimated_impact": "high",
            })

        frequent_trips = [
            c for c in circuit_data
            if c.get("total_trips", 0) > 5
        ]

        if frequent_trips:
            suggestions.append({
                "type": "frequent_trips",
                "severity": "medium",
                "title": "Circuit breakers instáveis",
                "description": f"{len(frequent_trips)} agentes com muitas aberturas",
                "action": "Ajustar thresholds ou investigar instabilidade",
                "estimated_impact": "medium",
            })

        return suggestions

    def _analyze_conferidor(self, stats: dict) -> list[dict]:
        suggestions = []

        dup_rate = stats.get("duplicate_rate", 0)
        if dup_rate > 0.1:
            suggestions.append({
                "type": "high_duplicates",
                "severity": "medium",
                "title": "Alta taxa de mensagens duplicadas",
                "description": f"{dup_rate:.1%} de duplicatas",
                "action": "Verificar se agentes estão enviando a mesma mensagem múltiplas vezes",
                "estimated_impact": "low",
            })

        reject_rate = stats.get("rejection_rate", 0)
        if reject_rate > 0.2:
            suggestions.append({
                "type": "high_rejection",
                "severity": "high",
                "title": "Alta taxa de rejeição no Conferidor",
                "description": f"{reject_rate:.1%} de rejeições",
                "action": "Revisar regras de validação ou mensagens dos agentes",
                "estimated_impact": "high",
            })

        rate_limit_rate = stats.get("total_rate_limited", 0) / max(stats.get("total_received", 1), 1)
        if rate_limit_rate > 0.05:
            suggestions.append({
                "type": "rate_limiting",
                "severity": "medium",
                "title": "Muitos agentes atingindo rate limit",
                "description": f"{rate_limit_rate:.1%} de rate limiting",
                "action": "Aumentar limites ou otimizar frequência de mensagens",
                "estimated_impact": "medium",
            })

        return suggestions

    def _calculate_health_score(
        self,
        metrics: dict,
        reputation: list[dict],
        circuits: list[dict],
    ) -> float:
        score = 1.0

        health = metrics.get("health", {})
        score *= health.get("score", 0.5)

        open_circuits = len([c for c in circuits if c.get("state") == "open"])
        score -= open_circuits * 0.05

        low_rep = len([
            r for r in reputation
            if r.get("overall_score", 1) < 0.3
        ])
        score -= low_rep * 0.02

        return max(0.0, min(1.0, score))

    async def handle_message(self, message: Message) -> dict | None:
        if message.event == EventType.DECISION_COMPLETED:
            return await self._on_decision_completed(message)
        return None

    async def _on_decision_completed(self, message: Message) -> dict:
        payload = message.payload
        if payload.get("verdict") == "REJEITADO":
            return {
                "action": "flag_rejection",
                "request_id": payload.get("request_id"),
                "suggestion": "Investigar padrão de rejeições recorrentes",
            }
        return {"action": "none"}
