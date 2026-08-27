import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("meta.analyst")


class AnalystAgent:
    """Meta-agente analista de padrões e tendências.

    Responsabilidades:
    - Detectar padrões nas decisões (aprovados/rejeitados)
    - Identificar tendências de performance ao longo do tempo
    - Analisar correlações entre agentes
    - Gerar insights acionáveis para melhoria
    - Prever gargalos antes que aconteçam
    """

    def __init__(self):
        self.agent_id = "meta-analyst"
        self.decision_history: list[dict] = []
        self.pattern_cache: list[dict] = []

    async def analyze_decisions(
        self,
        recent_decisions: list[dict],
    ) -> dict[str, Any]:
        """Analisa decisões recentes e identifica padrões."""
        patterns = []

        patterns.extend(self._detect_verdict_patterns(recent_decisions))
        patterns.extend(self._detect_agent_patterns(recent_decisions))
        patterns.extend(self._detect_time_patterns(recent_decisions))
        patterns.extend(self._detect_conflict_patterns(recent_decisions))

        insights = self._generate_insights(patterns, recent_decisions)

        analysis = {
            "timestamp": time.time(),
            "decisions_analyzed": len(recent_decisions),
            "patterns_found": len(patterns),
            "patterns": patterns,
            "insights": insights,
            "confidence": self._calculate_confidence(patterns, recent_decisions),
        }

        self.pattern_cache.append(analysis)
        if len(self.pattern_cache) > 100:
            self.pattern_cache = self.pattern_cache[-50:]

        logger.info(
            f"Análise de padrões: {len(patterns)} padrões, "
            f"{len(insights)} insights"
        )

        return analysis

    def _detect_verdict_patterns(self, decisions: list[dict]) -> list[dict]:
        patterns = []

        verdicts = [d.get("result", {}).get("verdict", "") for d in decisions]
        total = len(verdicts)

        if total < 5:
            return patterns

        approve_rate = verdicts.count("APROVADO") / total
        reject_rate = verdicts.count("REJEITADO") / total

        if approve_rate > 0.8:
            patterns.append({
                "type": "high_approval",
                "description": f"Taxa de aprovação muito alta ({approve_rate:.0%})",
                "severity": "medium",
                "suggestion": "Verificar se agentes estão sendo muito permissivos",
            })

        if reject_rate > 0.5:
            patterns.append({
                "type": "high_rejection",
                "description": f"Taxa de rejeição alta ({reject_rate:.0%})",
                "severity": "high",
                "suggestion": "Revisar critérios de rejeição ou qualidade das propostas",
            })

        if total > 10:
            recent_verdicts = verdicts[-5:]
            if len(set(recent_verdicts)) == 1:
                patterns.append({
                    "type": "verdict_streak",
                    "description": f"Sequência de {len(recent_verdicts)} decisões iguais",
                    "severity": "low",
                    "suggestion": "Possível viés ou problema no pipeline de decisão",
                })

        return patterns

    def _detect_agent_patterns(self, decisions: list[dict]) -> list[dict]:
        patterns = []

        agent_votes: dict[str, list[str]] = {}
        for d in decisions:
            for resp in d.get("result", {}).get("agent_responses", []):
                agent = resp.get("agent", "")
                verdict = resp.get("verdict", "")
                if agent not in agent_votes:
                    agent_votes[agent] = []
                agent_votes[agent].append(verdict)

        for agent, votes in agent_votes.items():
            total = len(votes)
            if total < 5:
                continue

            approve_rate = votes.count("APROVADO") / total
            if approve_rate > 0.95:
                patterns.append({
                    "type": "agent_rubber_stamp",
                    "agent": agent,
                    "description": f"Agente {agent} aprova quase tudo ({approve_rate:.0%})",
                    "severity": "medium",
                    "suggestion": f"Revisar critérios do agente {agent}",
                })

            if approve_rate < 0.1:
                patterns.append({
                    "type": "agent_veto",
                    "agent": agent,
                    "description": f"Agente {agent} rejeita quase tudo ({1-approve_rate:.0%})",
                    "severity": "medium",
                    "suggestion": f"Verificar se {agent} está muito conservador",
                })

        return patterns

    def _detect_time_patterns(self, decisions: list[dict]) -> list[dict]:
        patterns = []

        if len(decisions) < 20:
            return patterns

        timestamps = []
        for d in decisions:
            ts = d.get("processed_at")
            if ts:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts)
                    timestamps.append(dt.hour)
                except (ValueError, TypeError):
                    pass

        if not timestamps:
            return patterns

        hour_counts = {}
        for h in timestamps:
            hour_counts[h] = hour_counts.get(h, 0) + 1

        peak_hour = max(hour_counts, key=hour_counts.get)
        peak_count = hour_counts[peak_hour]

        if peak_count > len(timestamps) * 0.3:
            patterns.append({
                "type": "peak_hours",
                "description": f"Pico de atividade às {peak_hour}h ({peak_count} decisões)",
                "severity": "low",
                "suggestion": "Considerar escalabilidade para horários de pico",
            })

        return patterns

    def _detect_conflict_patterns(self, decisions: list[dict]) -> list[dict]:
        patterns = []

        conflicts = 0
        for d in decisions:
            agent_responses = d.get("result", {}).get("agent_responses", [])
            verdicts = [r.get("verdict", "") for r in agent_responses]
            if len(set(verdicts)) > 1:
                conflicts += 1

        if len(decisions) > 0:
            conflict_rate = conflicts / len(decisions)
            if conflict_rate > 0.3:
                patterns.append({
                    "type": "high_conflicts",
                    "description": f"Alta taxa de conflito entre agentes ({conflict_rate:.0%})",
                    "severity": "high",
                    "suggestion": "Revisar alinhamento dos critérios entre agentes",
                })

        return patterns

    def _generate_insights(
        self, patterns: list[dict], decisions: list[dict]
    ) -> list[str]:
        insights = []

        high_severity = [p for p in patterns if p.get("severity") == "high"]
        if high_severity:
            insights.append(
                f"ATENÇÃO: {len(high_severity)} padrões de alta severidade detectados"
            )

        if not patterns:
            insights.append("Sistema operando dentro dos parâmetros normais")

        verdict_dist = {}
        for d in decisions:
            v = d.get("result", {}).get("verdict", "UNKNOWN")
            verdict_dist[v] = verdict_dist.get(v, 0) + 1

        if verdict_dist:
            main_verdict = max(verdict_dist, key=verdict_dist.get)
            insights.append(f"Veredito predominante: {main_verdict}")

        return insights

    def _calculate_confidence(
        self, patterns: list[dict], decisions: list[dict]
    ) -> float:
        if len(decisions) < 5:
            return 0.3
        if len(decisions) < 20:
            return 0.5
        if len(decisions) < 50:
            return 0.7
        return 0.9

    async def handle_message(self, message: Message) -> dict | None:
        if message.event == EventType.DECISION_COMPLETED:
            self.decision_history.append({
                "id": message.id,
                "sender": message.sender,
                "payload": message.payload,
                "timestamp": message.timestamp,
            })
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-500:]
        return None
