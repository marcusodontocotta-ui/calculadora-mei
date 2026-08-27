from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.nexus")

TECH_STACKS = {
    "python": ["fastapi", "django", "flask", "celery", "redis", "postgresql", "docker"],
    "javascript": ["node", "react", "vue", "angular", "express", "nextjs"],
    "infra": ["docker", "kubernetes", "terraform", "aws", "gcp", "azure", "cloud"],
    "data": ["postgres", "mysql", "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq"],
    "ai": ["openai", "anthropic", "tensorflow", "pytorch", "huggingface", "langchain"],
}


class NexusAgent:
    def __init__(self):
        self.agent_id = "nexus"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"Nexus analisando viabilidade tecnica: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        risks = []
        recommendations = []
        confidence = 0.6

        detected_stacks = {}
        for stack, keywords in TECH_STACKS.items():
            hits = [kw for kw in keywords if kw in full_text]
            if hits:
                detected_stacks[stack] = hits
                confidence += 0.05

        if detected_stacks:
            stacks_str = ", ".join(f"{k}({','.join(v[:2])})" for k, v in detected_stacks.items())
            risks.append(f"Tecnologias detectadas: {stacks_str}")

        has_database = any(k in full_text for k in ["banco de dados", "database", "postgresql", "mysql", "mongodb", "armazenamento"])
        if has_database:
            risks.append("Componente de persistencia identificado - considerar escalabilidade e backup")
            recommendations.append("Definir estrategia de backup e replicacao de dados")

        has_async = any(k in full_text for k in ["async", "assincrono", "fila", "queue", "celery", "worker", "background"])
        if has_async:
            recommendations.append("Implementar processamento assincrono para tarefas de longa duracao")

        has_api = any(k in full_text for k in ["api", "endpoint", "rest", "graphql", "microservico"])
        if has_api:
            risks.append("Integracao via API detectada - considerar versionamento e rate limiting")
            recommendations.append("Implementar versionamento de API e documentacao OpenAPI")

        has_real_time = any(k in full_text for k in ["real-time", "tempo real", "websocket", "sse", "push", "notificacao"])
        if has_real_time:
            risks.append("Requisito de tempo real - infraestrutura adequada necessaria")
            recommendations.append("Avaliar WebSockets ou Server-Sent Events para comunicacao real-time")

        has_scalability = any(k in full_text for k in ["escala", "milhoes", "milhao", "crescimento", "horizontal", "cluster"])
        if has_scalability:
            recommendations.append("Projetar para escalabilidade horizontal desde o inicio")

        has_monitoring = any(k in full_text for k in ["monitoramento", "metricas", "logs", "observabilidade", "health check"])
        if not has_monitoring:
            risks.append("Sistema sem monitoramento especificado - adicionar observabilidade")
            recommendations.append("Implementar stack de observabilidade (metrics, logs, traces)")

        if not risks:
            risks.append("Nenhum risco tecnico critico identificado")
            confidence = 0.5

        confidence = min(confidence, 0.95)

        if not recommendations:
            recommendations.append("Validar stack tecnologica com equipe antes da implementacao")

        verdict = "APROVADO"
        if len(risks) > 3:
            verdict = "CONDICIONAL"

        return DecisionResponse(
            request_id=request.id,
            agent_id=self.agent_id,
            agent_role="nexus",
            verdict=verdict,
            reasoning=f"Viabilidade tecnica avaliada. Stack detectado: {list(detected_stacks.keys()) or 'generico'}. {len(risks)} riscos identificados.",
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
        )
