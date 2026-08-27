from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.apolo")


class ApoloAgent:
    """Coordenador/sintetizador - avaliacao holistica e final."""

    def __init__(self):
        self.agent_id = "apolo"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"Apolo realizando avaliacao holistica: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        risks = []
        recommendations = []
        confidence = 0.65

        complexity_score = 0

        if len(request.description) > 500:
            complexity_score += 1
            risks.append("Descricao longa - possivel alta complexidade")

        if request.constraints:
            complexity_score += 1
            risks.append(f"{len(request.constraints)} restricoes definidas")

        if request.context:
            context_keys = len(request.context)
            if context_keys > 5:
                complexity_score += 1
                risks.append("Contexto extenso - multiplos fatores a considerar")

        priority = getattr(request, "priority", 5)
        if priority >= 8:
            risks.append(f"Prioridade alta ({priority}/10) - requisito critico")
            recommendations.append("Alocar recursos prioritarios e definir milestones claros")

        has_docker = "docker" in full_text
        has_ai = any(k in full_text for k in ["ia", "inteligencia artificial", "openai", "llm", "gpt", "anthropic"])
        has_database = any(k in full_text for k in ["banco", "database", "postgres", "mysql", "mongo"])

        components = sum([has_docker, has_ai, has_database])
        if components >= 2:
            complexity_score += 1
            risks.append(f"Sistema com {components} componentes principais identificados")

        if complexity_score >= 3:
            recommendations.append("Dividir em fases de implementacao para reduzir risco")
            recommendations.append("Implementar validacao continua com feedback loop")

        recommendations.append("Definir criterios de sucesso claros e mensuraveis")
        recommendations.append("Estabelecer processo de revisao periodica")

        if not risks:
            risks.append("Projeto de complexidade gerenciavel")
            confidence = 0.6

        confidence = min(confidence + (complexity_score * 0.02), 0.95)

        if complexity_score >= 4:
            verdict = "CONDICIONAL"
        elif complexity_score >= 2:
            verdict = "APROVADO"
        else:
            verdict = "APROVADO"

        return DecisionResponse(
            request_id=request.id,
            agent_id=self.agent_id,
            agent_role="apolo",
            verdict=verdict,
            reasoning=f"Avaliacao holistica: complexidade={complexity_score}/5, componentes={components}, prioridade={priority}/10.",
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
        )
