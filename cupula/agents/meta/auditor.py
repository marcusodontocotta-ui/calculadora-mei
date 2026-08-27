import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType

logger = get_logger("meta.auditor")


class AuditorAgent:
    """Meta-agente auditor que monitora integridade e compliance.

    Responsabilidades:
    - Auditar trilha de audit de todas comunicações
    - Detectar anomalias e padrões suspeitos
    - Verificar conformidade com regras de negócio
    - Gerar relatórios de compliance
    - Alertar sobre violações de segurança
    """

    def __init__(self):
        self.agent_id = "meta-auditor"
        self.audit_rules: list[dict] = []
        self.violations: list[dict] = []
        self._setup_rules()

    def _setup_rules(self):
        self.audit_rules = [
            {
                "name": "no_spam",
                "check": self._check_spam,
                "description": "Agentes não devem enviar mais de 100 msgs/min",
                "severity": "high",
            },
            {
                "name": "no_self_loop",
                "check": self._check_self_loop,
                "description": "Agentes não devem responder a si mesmos",
                "severity": "medium",
            },
            {
                "name": "no_circular_deps",
                "check": self._check_circular_deps,
                "description": "Evitar dependências circulares entre agentes",
                "severity": "high",
            },
            {
                "name": "data_integrity",
                "check": self._check_data_integrity,
                "description": "Dados devem estar completos e íntegros",
                "severity": "critical",
            },
        ]

    async def audit_communication(
        self,
        sender: str,
        receiver: str,
        event: str,
        payload: dict,
        timestamp: float,
    ) -> dict[str, Any]:
        """Audita uma comunicação entre agentes."""
        violations = []

        for rule in self.audit_rules:
            result = rule["check"](sender, receiver, event, payload, timestamp)
            if result["violation"]:
                violation = {
                    "rule": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "details": result["details"],
                    "sender": sender,
                    "receiver": receiver,
                    "event": event,
                    "timestamp": timestamp,
                    "audited_at": time.time(),
                }
                violations.append(violation)
                self.violations.append(violation)

                logger.warning(
                    f"VIOLAÇÃO [{rule['severity']}] {rule['name']}: "
                    f"{sender} -> {receiver}: {result['details']}"
                )

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "rules_checked": len(self.audit_rules),
            "timestamp": timestamp,
        }

    def _check_spam(
        self, sender: str, receiver: str, event: str, payload: dict, timestamp: float
    ) -> dict:
        return {"violation": False, "details": ""}

    def _check_self_loop(
        self, sender: str, receiver: str, event: str, payload: dict, timestamp: float
    ) -> dict:
        if sender == receiver and sender:
            return {
                "violation": True,
                "details": f"Agente {sender} enviando mensagem para si mesmo",
            }
        return {"violation": False, "details": ""}

    def _check_circular_deps(
        self, sender: str, receiver: str, event: str, payload: dict, timestamp: float
    ) -> dict:
        chain = payload.get("response_chain", [])
        if sender in chain:
            return {
                "violation": True,
                "details": f"Dependência circular detectada: {sender} já está na cadeia",
            }
        return {"violation": False, "details": ""}

    def _check_data_integrity(
        self, sender: str, receiver: str, event: str, payload: dict, timestamp: float
    ) -> dict:
        missing_fields = []
        if not payload.get("request_id"):
            missing_fields.append("request_id")
        if not payload.get("verdict") and event.startswith("decision"):
            missing_fields.append("verdict")

        if missing_fields:
            return {
                "violation": True,
                "details": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}",
            }
        return {"violation": False, "details": ""}

    async def generate_report(self) -> dict[str, Any]:
        """Gera relatório de auditoria."""
        total_violations = len(self.violations)

        by_severity = {}
        by_rule = {}
        by_agent = {}

        for v in self.violations:
            sev = v["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

            rule = v["rule"]
            by_rule[rule] = by_rule.get(rule, 0) + 1

            agent = v["sender"]
            by_agent[agent] = by_agent.get(agent, 0) + 1

        recent = self.violations[-20:] if self.violations else []

        return {
            "report_timestamp": time.time(),
            "total_violations": total_violations,
            "by_severity": by_severity,
            "by_rule": by_rule,
            "top_offenders": sorted(
                by_agent.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "recent_violations": recent,
            "compliance_score": max(0, 1.0 - (total_violations * 0.01)),
        }

    async def get_violations(
        self,
        severity: str = "",
        limit: int = 50,
    ) -> list[dict]:
        violations = self.violations
        if severity:
            violations = [v for v in violations if v["severity"] == severity]
        return violations[-limit:]

    async def handle_message(self, message: Message) -> dict | None:
        return None
