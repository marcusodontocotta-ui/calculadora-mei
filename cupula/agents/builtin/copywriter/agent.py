"""
Agente Copywriter - Especialista em textos de conversao
Analisa e melhora copy de landing pages e anuncios
"""
from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.copywriter")

COPY_KEYWORDS = [
    "copy", "texto", "titulo", "subtitulo", "descricao",
    "persuasao", "conversao", "gatilho", "beneficio", "dor",
    "prova social", "urgencia", "escassez", "cta", "chamada"
]

PSYCHOLOGICAL_TRIGGERS = {
    "dor": "Mencionar problemas do publico alvo",
    "beneficio": "Mostrar o que ganha, nao o que e",
    "prova_social": "Numeros, depoimentos, logos",
    "urgencia": "Timer, vagas limitadas, preco atual",
    "escassez": "Quantidade limitada, tempo limitado",
    "autoridade": "Especialista, certificacao, experiencia",
    " reciprocidade": "Dar algo gratis antes de pedir"
}

POWER_WORDS = [
    "gratis", "facil", "rapido", "simples", "seguro",
    "economize", "aumente", "elimine", "descubra", "comece",
    "garanta", "assegure", "proteja", "otimize", "simplifique"
]


class CopywriterAgent:
    def __init__(self):
        self.agent_id = "copywriter"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"Copywriter analisando: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        recommendations = []
        confidence = 0.6
        risks = []

        # Detectar publico alvo
        is_mei = any(k in full_text for k in ["mei", "microempreendedor", "individual"])
        is_b2c = any(k in full_text for k in ["consumidor", "pessoa fisica", "cliente final"])
        is_b2b = any(k in full_text for k in ["empresa", "corporativo", "b2b"])

        if is_mei:
            recommendations.append("Linguagem simples: 'Voce paga R$ 150' em vez de 'aliquota de 15%'")
            recommendations.append("Falar na dor: 'Medo de errar? Multa de 2% ao dia?'")
            confidence += 0.1

        # Analisar gatilhos mentais
        if any(k in full_text for k in ["urgencia", "agora", "hoje"]):
            recommendations.append("Adicionar timer ou data limite para criar urgencia")
            confidence += 0.05

        if any(k in full_text for k in ["gratis", "free", "trial"]):
            recommendations.append("Freemium e poderoso: 'Comece gratis, pague so se precisar'")
            confidence += 0.05

        # Analisar CTA
        if any(k in full_text for k in ["cta", "botao", "call to action"]):
            recommendations.append("CTA recomendado: 'Comecar Gratis' ou 'Testar Agora'")
            recommendations.append("Evitar: 'Clique aqui', 'Saiba mais', 'Enviar'")
            confidence += 0.05

        # Analisar prova social
        if any(k in full_text for k in ["depoimento", "review", "avaliacao"]):
            recommendations.append("Prova social forte: numeros reais ('22M de MEIs no Brasil')")
            confidence += 0.05

        # Riscos de copy
        if any(k in full_text for k in ["jargao", "tecnico", "complexo"]):
            risks.append("Texto pode estar muito tecnico - simplificar linguagem")
            confidence -= 0.1

        if len(full_text) > 1000:
            risks.append("Texto muito longo - landing pages conversam melhor com textos curtos")
            confidence -= 0.05

        return DecisionResponse(
            request_id=request.request_id,
            agent_id=self.agent_id,
            verdict="APROVADO" if confidence > 0.6 else "CONDICIONAL",
            confidence=min(confidence, 0.95),
            rationale=f"Analise de copy concluida com {len(recommendations)} recomendacoes",
            risks=risks,
            recommendations=recommendations
        )
