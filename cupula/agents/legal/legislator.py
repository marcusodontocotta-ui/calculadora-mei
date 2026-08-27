import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.legal_gateway.models import (
    LegalRequest,
    LegalReference,
    LegalSeverity,
    LegalVerdict,
)

logger = get_logger("legal.legislator")


class LegislatorAgent:
    """Agente Intérprete de Leis.

    Responsabilidades:
    - Interpretar textos legais e identificar leis aplicáveis
    - Fornecer numeração exata das leis (Lei nº X.XXX/AAAA)
    - Citar artigos específicos relevantes
    - Explicar em linguagem acessível o que a lei diz
    - Identificar conflitos entre leis
    - Verificar vigência e atualizações
    """

    def __init__(self):
        self.agent_id = "legislator"
        self._interpretation_cache: dict[str, dict] = {}

    async def analyze(
        self,
        request: LegalRequest,
        leis_por_dominio: dict[str, list[LegalReference]],
    ) -> dict[str, Any]:
        """Analisa request e identifica leis aplicáveis com interpretação."""
        logger.info(f"Interpretando leis para: {request.titulo}")

        leis_encontradas = []
        interpretacoes = []
        conflitos = []

        for dominio, leis in leis_por_dominio.items():
            for lei in leis:
                relevancia = self._calcular_relevancia(lei, request)
                if relevancia > 0.3:
                    interpretacao = self._interpretar_lei(lei, request)
                    leis_encontradas.append({
                        "lei": lei.lei_numero,
                        "orgao": lei.orgao,
                        "titulo": lei.titulo,
                        "relevancia": relevancia,
                        "artigos": lei.artigos_relevantes,
                    })
                    interpretacoes.append(interpretacao)

        conflitos = self._detectar_conflitos(leis_encontradas)

        if not leis_encontradas:
            veredito = LegalVerdict.REVISAO_NECESSARIA
            risco = LegalSeverity.MEDIA
            parecer = (
                "Não foram encontradas leis específicas que regulem esta ação. "
                "Recomenda-se consulta jurídica especializada."
            )
        elif conflitos:
            veredito = LegalVerdict.CONDICIONAL
            risco = LegalSeverity.ALTA
            parecer = self._gerar_parecer_com_conflitos(
                leis_encontradas, interpretacoes, conflitos
            )
        else:
            veredito = LegalVerdict.CONFORME
            risco = LegalSeverity.BAIXA
            parecer = self._gerar_parecer_clean(leis_encontradas, interpretacoes)

        return {
            "veredito": veredito,
            "risco": risco,
            "parecer": parecer,
            "leis_identificadas": len(leis_encontradas),
            "recomendacoes": self._gerar_recomendacoes(
                leis_encontradas, conflitos, request
            ),
            "conflitos": conflitos,
        }

    def _calcular_relevancia(
        self, lei: LegalReference, request: LegalRequest
    ) -> float:
        score = 0.0

        texto = (request.descricao + " " + request.acao_proposta).lower()

        for kw in lei.palavras_chave:
            if kw in texto:
                score += 0.2

        for dominio in request.dominios:
            if dominio == lei.dominio:
                score += 0.3

        return min(1.0, score)

    def _interpretar_lei(
        self, lei: LegalReference, request: LegalRequest
    ) -> dict[str, Any]:
        texto = (request.descricao + " " + request.acao_proposta).lower()

        artigos_aplicaveis = []
        for artigo in lei.artigos_relevantes:
            for kw in lei.palavras_chave:
                if kw in texto:
                    artigos_aplicaveis.append(artigo)
                    break

        if not artigos_aplicaveis:
            artigos_aplicaveis = lei.artigos_relevantes[:3]

        return {
            "lei": lei.lei_numero,
            "titulo": lei.titulo,
            "ementa": lei.ementa,
            "artigos_aplicaveis": artigos_aplicaveis,
            "explicacao": self._explicar_aplicacao(lei, request),
            "obrigacoes": self._identificar_obrigacoes(lei, request),
            "direitos": self._identificar_direitos(lei, request),
        }

    def _explicar_aplicacao(
        self, lei: LegalReference, request: LegalRequest
    ) -> str:
        explicacoes = {
            "13.709/2018": (
                "A LGPD (Lei nº 13.709/2018) regula o tratamento de dados pessoais. "
                "Toda operação com dados de pessoas identificadas ou identificáveis "
                "deve ter base legal (art. 7º), como consentimento, obrigação legal, "
                "ou legítimo interesse. O titular dos dados tem direitos como acesso, "
                "correção e exclusão (art. 18)."
            ),
            "8.078/1990": (
                "O CDC (Lei nº 8.078/1990) protege o consumidor contra práticas "
                "abusivas, vícios de produtos e defeitos de serviços. O fornecedor "
                "responde objetivamente por danos (art. 12). O consumidor pode "
                "desistir de compra em 7 dias (art. 49)."
            ),
            "14.195/2021": (
                "A Lei Complementar (Lei nº 14.195/2021) simplifica a abertura de empresas. "
                "O MEI pode faturar até R$ 81.000/ano. Empresas do Simples Nacional "
                "têm regime tributário simplificado."
            ),
            "12.965/2014": (
                "O Marco Civil (Lei nº 12.965/2014) garante neutralidade da internet, "
                "liberdade de expressão e proteção da privacidade. provedores não "
                "podem monitorar conteúdo sem ordem judicial (art. 7º)."
            ),
        }

        return explicacoes.get(
            lei.lei_numero,
            f"A {lei.titulo} (Lei nº {lei.lei_numero}) regulamenta {lei.dominio}. "
            f"Artigos relevantes: {', '.join(lei.artigos_relevantes)}.",
        )

    def _identificar_obrigacoes(
        self, lei: LegalReference, request: LegalRequest
    ) -> list[str]:
        obrigacoes_map = {
            "13.709/2018": [
                "Obter consentimento para tratamento de dados (art. 7º)",
                "Informar finalidade do tratamento (art. 9º)",
                "Designar Encarregado de Dados (art. 41)",
                "Comunicar incidentes de segurança à ANPD (art. 48)",
                "Manter registro de operações de tratamento (art. 37)",
            ],
            "8.078/1990": [
                "Fornecer informações claras sobre produtos/serviços (art. 6º)",
                "Garantir qualidade e segurança dos produtos (art. 12)",
                "Responder por danos causados ao consumidor (art. 14)",
                "Respeitar o direito de arrependimento em 7 dias (art. 49)",
            ],
            "14.195/2021": [
                "Manter contabilidade organizada",
                "Emitir notas fiscais",
                "Cumprir obrigações acessórias (DAS para MEI)",
            ],
        }

        return obrigacoes_map.get(
            lei.lei_numero,
            ["Cumprir as disposições da legislação vigente"],
        )

    def _identificar_direitos(
        self, lei: LegalReference, request: LegalRequest
    ) -> list[str]:
        direitos_map = {
            "13.709/2018": [
                "Direito de acesso aos dados pessoais (art. 18, I)",
                "Direito de correção de dados incompletos (art. 18, III)",
                "Direito de exclusão de dados desnecessários (art. 18, VI)",
                "Direito de portabilidade de dados (art. 18, V)",
                "Direito de oposição ao tratamento (art. 18, IX)",
            ],
            "8.078/1990": [
                "Direito de proteção contra práticas abusivas (art. 6º, IV)",
                "Direito de arrependimento em 7 dias (art. 49)",
                "Direito de reclamação ao PROCON",
                "Direito de ação por danos materiais e morais",
            ],
        }

        return direitos_map.get(
            lei.lei_numero,
            ["Direitos previstos na legislação aplicável"],
        )

    def _detectar_conflitos(
        self, leis: list[dict]
    ) -> list[dict[str, Any]]:
        conflitos = []

        for i, lei1 in enumerate(leis):
            for lei2 in leis[i + 1:]:
                if lei1["lei"] != lei2["lei"]:
                    conflitos_potenciais = {
                        ("13.709/2018", "12.965/2014"): (
                            "Possível conflito entre LGPD e Marco Civil "
                            "sobre coleta de dados em plataformas digitais"
                        ),
                    }

                    pair = tuple(sorted([lei1["lei"], lei2["lei"]]))
                    if pair in conflitos_potenciais:
                        conflitos.append({
                            "leis": [lei1["lei"], lei2["lei"]],
                            "tipo": "conflito_normativo",
                            "descricao": conflitos_potenciais[pair],
                            "severidade": "media",
                        })

        return conflitos

    def _gerar_parecer_clean(
        self, leis: list[dict], interpretacoes: list[dict]
    ) -> str:
        parts = [
            "=== PARECER DO LEGISLATOR ===\n",
            "Leis identificadas e aplicáveis:\n",
        ]

        for interp in interpretacoes:
            parts.append(f"• Lei nº {interp['lei']} - {interp['titulo']}")
            parts.append(f"  Artigos: {', '.join(interp['artigos_aplicaveis'])}")
            parts.append(f"  {interp['explicacao']}\n")

            if interp["obrigacoes"]:
                parts.append("  Obrigações:")
                for ob in interp["obrigacoes"][:3]:
                    parts.append(f"    - {ob}")

            if interp["direitos"]:
                parts.append("  Direitos:")
                for d in interp["direitos"][:3]:
                    parts.append(f"    - {d}")
            parts.append("")

        parts.append("Conclusão: Ação compatível com a legislação vigente.")
        return "\n".join(parts)

    def _gerar_parecer_com_conflitos(
        self,
        leis: list[dict],
        interpretacoes: list[dict],
        conflitos: list[dict],
    ) -> str:
        parts = [
            "=== PARECER DO LEGISLATOR (COM ALERTAS) ===\n",
            "Leis identificadas:\n",
        ]

        for interp in interpretacoes:
            parts.append(f"• Lei nº {interp['lei']} - {interp['titulo']}")

        parts.append("\n⚠ CONFLITOS DETECTADOS:")
        for c in conflitos:
            parts.append(f"  • {c['descricao']}")

        parts.append(
            "\nConclusão: Ação requer análise cuidadosa devido a conflitos normativos."
        )
        return "\n".join(parts)

    def _gerar_recomendacoes(
        self,
        leis: list[dict],
        conflitos: list[dict],
        request: LegalRequest,
    ) -> list[str]:
        recs = []

        if conflitos:
            recs.append("Consultar advogado especializado para análise de conflitos normativos")

        if "dados_pessoais" in request.dominios:
            recs.append("Verificar compliance com LGPD antes de prosseguir")
            recs.append("Designar Encarregado de Dados se ainda não designado")

        if "consumidor" in request.dominios:
            recs.append("Garantir transparência nas informações ao consumidor")

        if "digital" in request.dominios:
            recs.append("Validar assinaturas eletrônicas conforme Lei nº 14.063/2020")

        if not leis:
            recs.append("Realizar pesquisa legislativa mais aprofundada")
            recs.append("Solicitar parecer jurídico externo")

        return recs
