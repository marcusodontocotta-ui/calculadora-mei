"""
Agente UX/UI - Especialista em design e usabilidade
Analisa e melhora layouts de aplicacoes web
"""
from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest, DecisionResponse

logger = get_logger("builtin.uxui")

LAYOUT_KEYWORDS = [
    "layout", "design", "interface", "ui", "ux", "usabilidade",
    "cores", "tipografia", "espacamento", "responsivo", "mobile",
    "conversao", "cta", "landing page", "visual", "experiencia"
]

DESIGN_PATTERNS = {
    "hero_section": "Secao principal com titulo forte e CTA",
    "social_proof": "Prova social (numeros, depoimentos)",
    "feature_grid": "Grid de funcionalidades com icones",
    "comparison_table": "Tabela comparativa com concorrentes",
    "pricing_cards": "Cards de precos com destaque",
    "faq_accordion": "Perguntas frequentes em accordion",
    "cta_sections": "Chamadas para acao ao longo da pagina",
    "footer_links": "Rodape com links uteis"
}

COLOR_PSYCHOLOGY = {
    "azul": "Confianca, seguranca, profissionalismo",
    "verde": "Crescimento, dinheiro, aprovacao",
    "vermelho": "Urgencia, alerta, perigo",
    "laranja": "Acao, entusiasmo, energia",
    "preto": "Luxo, sofisticacao, elegancia",
    "branco": "Limpeza, simplicidade, espaco"
}


class UXUIAgent:
    def __init__(self):
        self.agent_id = "uxui"

    async def analyze(self, request: DecisionRequest) -> DecisionResponse:
        logger.info(f"UX/UI analisando: {request.title}")

        text = f"{request.title} {request.description}".lower()
        context_str = str(request.context).lower()
        full_text = f"{text} {context_str}"

        recommendations = []
        confidence = 0.6
        risks = []

        # Detectar tipo de projeto
        is_landing_page = any(k in full_text for k in ["landing page", "site", "app web", "conversao"])
        is_mobile = any(k in full_text for k in ["mobile", "app", "responsivo"])

        if is_landing_page:
            recommendations.append("Usar estrutura de landing page: Hero > Dor > Solucao > Prova Social > CTA")
            confidence += 0.1

        if is_mobile:
            recommendations.append("Design mobile-first: minimo 320px, botao grande, area de toque minima 44px")
            confidence += 0.05

        # Analisar se menciona cores
        if any(c in full_text for c in ["cor", "cores", "azul", "verde"]):
            recommendations.append("Paleta de cores: Azul (confianca) + Verde (dinheiro) + Branco (limpeza)")
            confidence += 0.05

        # Analisar CTA
        if any(k in full_text for k in ["cta", "botao", "comprar", "assinar"]):
            recommendations.append("CTA deve ser: cor contrastante, texto em verbo (Comecar, Testar, Assinar)")
            confidence += 0.05

        # Analisar conversao
        if any(k in full_text for k in ["conversao", "vendas", "receita"]):
            recommendations.append("Elementos de conversao: timer, vagas limitadas, bonus, garantia")
            confidence += 0.05

        # Riscos de layout
        if any(k in full_text for k in ["muito texto", "poluido", "complexo"]):
            risks.append("Pagina pode estar sobrecarregada - usar espacamento e quebras visuais")
            confidence -= 0.1

        return DecisionResponse(
            request_id=request.request_id,
            agent_id=self.agent_id,
            verdict="APROVADO" if confidence > 0.6 else "CONDICIONAL",
            confidence=min(confidence, 0.95),
            rationale=f"Analise UX/UI concluida com {len(recommendations)} recomendacoes",
            risks=risks,
            recommendations=recommendations
        )
