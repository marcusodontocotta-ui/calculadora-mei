from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.sentinel")

SECURITY_KEYWORDS = [
    "seguranca", "segurança", "vulnerabilidade", "ataque", "hack", "criptografia",
    "autenticacao", "autorizacao", "permissao", "sandbox", "isolamento",
    "dados sensiveis", "dados sensíveis", "cripto", "firewall", "intrusao",
]

COMPLIANCE_KEYWORDS = [
    "lgpd", "gdpr", "compliance", "conformidade", "regulacao", "regulamentacao",
    "auditoria", "trilha", "log", "privacidade", "consentimento",
]


class SentinelAgent:
    def __init__(self):
        self.agent_id = "sentinel"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"Sentinel analisando: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        risks = []
        confidence = 0.6

        security_hits = [kw for kw in SECURITY_KEYWORDS if kw in full_text]
        compliance_hits = [kw for kw in COMPLIANCE_KEYWORDS if kw in full_text]

        if security_hits:
            risks.append(f"Aspectos de segurança detectados: {', '.join(security_hits[:3])}")
            confidence += 0.1

        if compliance_hits:
            risks.append(f"Aspectos de conformidade detectados: {', '.join(compliance_hits[:3])}")
            confidence += 0.1

        has_sensitive_data = any(k in full_text for k in ["dados pessoais", "dados sensiveis", "dados sensíveis", "lgpd", "privacy"])
        if has_sensitive_data:
            risks.append("Dados pessoais/sensiveis envolvidos - requer proteção especial")
            confidence += 0.1

        has_external_api = any(k in full_text for k in ["api", "externo", "webhook", "http", "rest"])
        if has_external_api:
            risks.append("Integracao externa detectada - validar endpoints e autenticacao")
            confidence += 0.05

        has_ai = any(k in full_text for k in ["ia", "inteligencia artificial", "machine learning", "ml", "llm", "openai", "gpt"])
        if has_ai:
            risks.append("Uso de IA detectado - validar vieses e transparencia")
            confidence += 0.05

        if not risks:
            risks.append("Nenhum risco critico de seguranca identificado na analise superficial")
            confidence = 0.5

        confidence = min(confidence, 0.95)

        if has_sensitive_data and not any("lgpd" in r for r in risks):
            risks.append("Obrigatoriedade de conformidade com LGPD para dados pessoais")

        recommendations = []
        if security_hits:
            recommendations.append("Implementar autenticacao robusta e criptografia em transito e repouso")
        if compliance_hits:
            recommendations.append("Verificar conformidade regulatoria antes da implementacao")
        if has_sensitive_data:
            recommendations.append("Implementar consentimento granular e politica de retencao de dados")
        if has_external_api:
            recommendations.append("Utilizar autenticacao OAuth2/JWT para APIs externas")
        if has_ai:
            recommendations.append("Documentar uso de IA e implementar mecanismos de auditoria de vieses")

        verdict = "APROVADO"
        if len(risks) > 3:
            verdict = "CONDICIONAL"

        return DecisionResponse(
            request_id=request.id,
            agent_id=self.agent_id,
            agent_role="sentinel",
            verdict=verdict,
            reasoning=f"Analise de seguranca realizada com {len(security_hits)} indicadores de seguranca e {len(compliance_hits)} de conformidade.",
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
        )
