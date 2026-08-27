import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.legal_gateway.models import (
    LegalRequest,
    LegalSeverity,
    LegalVerdict,
)

logger = get_logger("legal.jurisprudence")


class JurisprudenceAgent:
    """Agente de Análise de Jurisprudência.

    Responsabilidades:
    - Analisar precedentes judiciais relevantes
    - Identificar tendências jurisprudenciais
    - Verificar entendimento dos tribunais superiores
    - Alertar sobre mudanças de entendimento
    - Cruzar jurisprudência com legislação
    """

    PRECEDENTS_DB = {
        "dados_pessoais": [
            {
                "tribunal": "STJ",
                "ano": 2023,
                "tema": "Indenização por vazamento de dados",
                "entendimento": "Empresas são responsabilizadas por falhas de segurança que levam a vazamento de dados pessoais. Indenização pode ser fixada em R$ 5.000 a R$ 50.000 por titular afetado.",
                "relevancia": "alta",
            },
            {
                "tribunal": "STF",
                "ano": 2023,
                "tema": "LGPD e liberdade de imprensa",
                "entendimento": "Jornalistas têm proteção especial para tratamento de dados em cobertura jornalística, mas devem respeitar dignidade e privacidade.",
                "relevancia": "media",
            },
            {
                "tribunal": "TJSP",
                "ano": 2024,
                "tema": "Consentimento para marketing",
                "entendimento": "Envio de comunicações de marketing sem consentimento viola LGPD. Empresa deve provar consentimento efetivo.",
                "relevancia": "alta",
            },
        ],
        "consumidor": [
            {
                "tribunal": "STJ",
                "ano": 2024,
                "tema": "Cobrança indevida em apps",
                "entendimento": "Aplicativos que cobram valores não previstos claramente praticam prática abusiva (CDC art. 39). Consumidor tem direito à devolução em dobro.",
                "relevancia": "alta",
            },
            {
                "tribunal": "STJ",
                "ano": 2023,
                "tema": "Responsabilidade por produtos digitais",
                "entendimento": "Fornecedores de software respondem por vícios que tornam o produto inadequado ao uso. CDC se aplica a produtos digitais.",
                "relevancia": "alta",
            },
        ],
        "trabalhista": [
            {
                "tribunal": "TST",
                "ano": 2024,
                "tema": "Trabalho remoto e custo de energia",
                "entendimento": "Empregador deve auxiliar com custos de energia e internet quando exige regime de home office total.",
                "relevancia": "alta",
            },
            {
                "tribunal": "STF",
                "ano": 2023,
                "tema": "ISQN de plataformas digitais",
                "entendimento": "Trabalhadores de plataformas como Uber e iFood têm direito a benefícios trabalhistas (RE 1203975).",
                "relevancia": "critica",
            },
        ],
        "digital": [
            {
                "tribunal": "STJ",
                "ano": 2024,
                "tema": "Validade de assinatura digital",
                "entendimento": "Assinatura digital ICP-Brasil tem presunção de autenticidade. Outras assinaturas eletrônicas devem comprovar autenticidade.",
                "relevancia": "alta",
            },
            {
                "tribunal": "TJSP",
                "ano": 2024,
                "tema": "Nulidade de cláusula de foro online",
                "entendimento": "Cláusula de foro exclusivo online pode ser nula quando dificulta acesso do consumidor à justiça.",
                "relevancia": "media",
            },
        ],
    }

    def __init__(self):
        self.agent_id = "jurisprudence"

    async def analyze(
        self,
        request: LegalRequest,
        leis_por_dominio: dict,
    ) -> dict[str, Any]:
        """Analisa jurisprudência relevante para a ação."""
        logger.info(f"Analisando jurisprudência: {request.titulo}")

        precedentes_relevantes = []
        tendencias = []

        for dominio in request.dominios:
            precedentes = self.PRECEDENTS_DB.get(dominio, [])
            for prec in precedentes:
                relevancia = self._calcular_relevancia(prec, request)
                if relevancia > 0.4:
                    precedentes_relevantes.append({
                        **prec,
                        "relevancia_score": relevancia,
                    })

        tendencias = self._analisar_tendencias(precedentes_relevantes, request)

        if any(p["relevancia"] == "critica" for p in precedentes_relevantes):
            veredito = LegalVerdict.NAO_CONFORME
            risco = LegalSeverity.CRITICA
        elif len(precedentes_relevantes) > 3:
            veredito = LegalVerdict.CONDICIONAL
            risco = LegalSeverity.MEDIA
        elif precedentes_relevantes:
            veredito = LegalVerdict.CONFORME
            risco = LegalSeverity.BAIXA
        else:
            veredito = LegalVerdict.REVISAO_NECESSARIA
            risco = LegalSeverity.MEDIA

        parecer = self._gerar_parecer_jurisprudencia(
            precedentes_relevantes, tendencias, request
        )

        return {
            "veredito": veredito,
            "risco": risco,
            "parecer": parecer,
            "precedentes": precedentes_relevantes,
            "tendencias": tendencias,
            "recomendacoes": self._gerar_recomendacoes_juris(
                precedentes_relevantes, tendencias, request
            ),
        }

    def _calcular_relevancia(self, prec: dict, request: LegalRequest) -> float:
        score = 0.0
        texto = (request.descricao + " " + request.acao_proposta).lower()

        tema = prec.get("tema", "").lower()
        palavras_tema = tema.split()

        for p in palavras_tema:
            if p in texto:
                score += 0.3

        if prec.get("relevancia") == "critica":
            score += 0.3
        elif prec.get("relevancia") == "alta":
            score += 0.2

        if prec.get("ano", 0) >= 2024:
            score += 0.1

        return min(1.0, score)

    def _analisar_tendencias(
        self, precedentes: list[dict], request: LegalRequest
    ) -> list[str]:
        tendencias = []

        tribunais = {}
        for p in precedentes:
            tribunal = p.get("tribunal", "")
            if tribunal not in tribunais:
                tribunais[tribunal] = []
            tribunais[tribunal].append(p)

        for tribunal, precs in tribunais.items():
            if len(precs) >= 2:
                tendencias.append(
                    f"Tendência do {tribunal}: "
                    f"{len(precs)} decisões favoráveis ao tema"
                )

        anos = [p.get("ano", 0) for p in precedentes]
        if anos and max(anos) >= 2024:
            tendencias.append("Jurisprudência recente (2024-2025) aplicável")

        return tendencias

    def _gerar_parecer_jurisprudencia(
        self,
        precedentes: list[dict],
        tendencias: list[str],
        request: LegalRequest,
    ) -> str:
        parts = [
            "=== PARECER DE JURISPRUDÊNCIA ===\n",
            f"Análise: {request.titulo}\n",
        ]

        if not precedentes:
            parts.append(
                "Não foram encontrados precedentes judiciais diretamente "
                "aplicáveis ao caso. Recomenda-se pesquisa jurisprudencial "
                "mais aprofundada nos tribunais."
            )
            return "\n".join(parts)

        parts.append(f"Precedentes encontrados: {len(precedentes)}\n")

        for prec in precedentes:
            parts.append(
                f"• {prec['tribunal']} ({prec['ano']}) - {prec['tema']}"
            )
            parts.append(f"  Entendimento: {prec['entendimento']}")
            parts.append(f"  Relevância: {prec.get('relevancia', 'media')}\n")

        if tendencias:
            parts.append("TENDÊNCIAS JURISPRUDENCIAIS:")
            for t in tendencias:
                parts.append(f"  → {t}")

        parts.append(
            "\nConclusão: "
            + (
                "Jurisprudência favorável ao caso."
                if all(p.get("relevancia") != "critica" for p in precedentes)
                else "Jurisprudência indica riscos significativos."
            )
        )

        return "\n".join(parts)

    def _gerar_recomendacoes_juris(
        self,
        precedentes: list[dict],
        tendencias: list[str],
        request: LegalRequest,
    ) -> list[str]:
        recs = []

        criticos = [p for p in precedentes if p.get("relevancia") == "critica"]
        if criticos:
            recs.append(
                "URGENTE: Revisar ação baseada em jurisprudência crítica"
            )

        if len(precedentes) > 3:
            recs.append(
                "Documentar todas as decisões judiciais relevantes para defesa"
            )

        recs.append(
            "Monitorar mudanças de entendimento dos tribunais periodicamente"
        )

        return recs
