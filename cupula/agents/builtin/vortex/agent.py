from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.vortex")

BUSINESS_KEYWORDS = {
    "receita": ["monetizacao", "pricing", "assinatura", "freemium", "receita"],
    "mercado": ["mercado", "concorrencia", "competidor", "diferencial", "target", "publico"],
    "crescimento": ["crescimento", "escalabilidade", "replicavel", "scaling", "growth"],
    "risco_financeiro": ["custo", "investimento", "burn", "roi", "payback", "orçamento", "orcamento"],
}


class VortexAgent:
    def __init__(self):
        self.agent_id = "vortex"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"Vortex analisando viabilidade de negocio: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        risks = []
        recommendations = []
        confidence = 0.6

        detected_areas = {}
        for area, keywords in BUSINESS_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in full_text]
            if hits:
                detected_areas[area] = hits
                confidence += 0.05

        if "receita" in detected_areas:
            risks.append("Modelo de receita identificado - validar unit economics")
            recommendations.append("Definir KPIs de receita e validar unit economics antes do MVP")
        else:
            risks.append("Nenhum modelo de receita explicito identificado")
            recommendations.append("Definir modelo de monetizacao claro")

        if "mercado" in detected_areas:
            risks.append("Analise de mercado necessaria - validar produto-mercado fit")
            recommendations.append("Realizar pesquisa de mercado e entrevistas com clientes potenciais")
        else:
            recommendations.append("Conduzir analise competitiva e mapeamento de mercado")

        if "risco_financeiro" in detected_areas:
            risco_hits = detected_areas["risco_financeiro"]
            risks.append(f"Aspectos financeiros detectados: {', '.join(risco_hits[:3])}")
            recommendations.append("Criar projecao financeira com cenarios otimista, base e pessimista")

        if "crescimento" in detected_areas:
            recommendations.append("Definir metricas de crescimento e marcos de validacao")

        has_sla = any(k in full_text for k in ["sla", "uptime", "disponibilidade", "99.9", "99.99"])
        if has_sla:
            risks.append("Requisito de SLA identificado - impacto em custo e operacao")
            recommendations.append("Definir SLAs realistas com margem de tolerancia")

        has_mvp = any(k in full_text for k in ["mvp", "prototipo", "poc", "minimum viable"])
        if has_mvp:
            recommendations.append("Focar no MVP com features essenciais para validacao rapida")

        priority = getattr(request, "priority", 5)
        if priority >= 8:
            risks.append("Prioridade alta - garantir recursos suficientes e timeline realista")

        if not risks:
            risks.append("Nenhum risco de negocio critico identificado")
            confidence = 0.5

        confidence = min(confidence, 0.95)

        verdict = "APROVADO"
        if len(risks) > 3:
            verdict = "CONDICIONAL"

        return DecisionResponse(
            request_id=request.id,
            agent_id=self.agent_id,
            agent_role="vortex",
            verdict=verdict,
            reasoning=f"Viabilidade de negocio avaliada. Areas detectadas: {list(detected_areas.keys()) or 'nenhuma especifica'}.",
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
        )
