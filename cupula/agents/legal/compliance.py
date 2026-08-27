import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.legal_gateway.models import (
    LegalRequest,
    LegalReference,
    LegalSeverity,
    LegalVerdict,
)

logger = get_logger("legal.compliance")


class ComplianceAgent:
    """Agente de Compliance e Conformidade.

    Responsabilidades:
    - Verificar se ações estão em conformidade com leis
    - Identificar gaps de compliance
    - Sugerir medidas corretivas
    - Monitorar prazos regulatórios
    - Verificar documentação necessária
    """

    def __init__(self):
        self.agent_id = "compliance"
        self._checklists: dict[str, list[dict]] = {}
        self._load_checklists()

    def _load_checklists(self):
        self._checklists = {
            "dados_pessoais": [
                {"item": "Consentimento obtido", "obrigatorio": True, "artigo": "LGPD art. 7º"},
                {"item": "Finalidade clara informada", "obrigatorio": True, "artigo": "LGPD art. 9º"},
                {"item": "Encarregado de Dados designado", "obrigatorio": True, "artigo": "LGPD art. 41"},
                {"item": "Registro de operações de tratamento", "obrigatorio": True, "artigo": "LGPD art. 37"},
                {"item": "Política de privacidade publicada", "obrigatorio": True, "artigo": "LGPD art. 41"},
                {"item": "Plano de resposta a incidentes", "obrigatorio": True, "artigo": "LGPD art. 48"},
                {"item": "Avaliação de Impacto (RIPD)", "obrigatorio": False, "artigo": "LGPD art. 38"},
                {"item": "Transferência internacional validada", "obrigatorio": False, "artigo": "LGPD art. 33"},
            ],
            "consumidor": [
                {"item": "Informações claras sobre produto/serviço", "obrigatorio": True, "artigo": "CDC art. 6º"},
                {"item": "Preço visível e correto", "obrigatorio": True, "artigo": "CDC art. 48"},
                {"item": "Direito de arrependimento respeitado", "obrigatorio": True, "artigo": "CDC art. 49"},
                {"item": "Termos de uso claros", "obrigatorio": True, "artigo": "CDC art. 46"},
                {"item": "Canal de atendimento disponível", "obrigatorio": True, "artigo": "CDC art. 42"},
            ],
            "trabalhista": [
                {"item": "Contrato de trabalho formalizado", "obrigatorio": True, "artigo": "CLT art. 442"},
                {"item": "Registro em CTPS", "obrigatorio": True, "artigo": "CLT art. 29"},
                {"item": "Jornada controlada", "obrigatorio": True, "artigo": "CLT art. 74"},
                {"item": "FGTS recolhido", "obrigatorio": True, "artigo": "Lei 8.036/90"},
                {"item": "Equipamentos de proteção fornecidos", "obrigatorio": False, "artigo": "NR-6"},
            ],
            "empresarial": [
                {"item": "Contrato social vigente", "obrigatorio": True, "artigo": "Lei 6.404/76"},
                {"item": "Inscrições estadual/municipal", "obrigatorio": True, "artigo": "Varia por estado"},
                {"item": "Certificado digital válido", "obrigatorio": False, "artigo": "ICP-Brasil"},
                {"item": "Capital social integralizado", "obrigatorio": True, "artigo": "Lei 6.404/76 art. 100"},
            ],
            "digital": [
                {"item": "Assinatura eletrônica qualificada", "obrigatorio": True, "artigo": "Lei 14.063/20 art. 4º"},
                {"item": "Cadeia de confiança validada", "obrigatorio": True, "artigo": "Lei 14.063/20 art. 5º"},
                {"item": "Armazenamento seguro garantido", "obrigatorio": True, "artigo": "Lei 13.787/18"},
            ],
        }

    async def analyze(
        self,
        request: LegalRequest,
        leis_por_dominio: dict[str, list[LegalReference]],
    ) -> dict[str, Any]:
        """Verifica conformidade da ação com as leis."""
        logger.info(f"Verificando compliance: {request.titulo}")

        checklist_results = []
        gaps_encontrados = []
        conformidades = []

        for dominio in request.dominios:
            checklist = self._checklists.get(dominio, [])
            for item in checklist:
                status = self._verificar_item(item, request)
                checklist_results.append({
                    "dominio": dominio,
                    "item": item["item"],
                    "status": status,
                    "obrigatorio": item["obrigatorio"],
                    "artigo": item["artigo"],
                })

                if status == "pendente" and item["obrigatorio"]:
                    gaps_encontrados.append({
                        "item": item["item"],
                        "dominio": dominio,
                        "artigo": item["artigo"],
                        "severidade": "alta" if item["obrigatorio"] else "media",
                    })
                elif status == "atendido":
                    conformidades.append(item["item"])

        if gaps_encontrados:
            gaps_criticos = [g for g in gaps_encontrados if g["severidade"] == "alta"]
            if gaps_criticos:
                veredito = LegalVerdict.NAO_CONFORME
                risco = LegalSeverity.ALTA
            else:
                veredito = LegalVerdict.CONDICIONAL
                risco = LegalSeverity.MEDIA
        else:
            veredito = LegalVerdict.CONFORME
            risco = LegalSeverity.BAIXA

        parecer = self._gerar_parecer_compliance(
            checklist_results, gaps_encontrados, conformidades, request
        )

        return {
            "veredito": veredito,
            "risco": risco,
            "parecer": parecer,
            "gaps": gaps_encontrados,
            "conformidades": conformidades,
            "recomendacoes": self._gerar_recomendacoes_compliance(
                gaps_encontrados, request
            ),
        }

    def _verificar_item(self, item: dict, request: LegalRequest) -> str:
        texto = (
            request.descricao + " " + request.acao_proposta + " "
            + str(request.contexto)
        ).lower()

        palavras_item = item["item"].lower().split()

        for palavra in palavras_item[:3]:
            if palavra in texto:
                return "atendido"

        return "pendente"

    def _gerar_parecer_compliance(
        self,
        checklist: list[dict],
        gaps: list[dict],
        conformidades: list[str],
        request: LegalRequest,
    ) -> str:
        parts = [
            "=== PARECER DE COMPLIANCE ===\n",
            f"Análise: {request.titulo}",
            f"Domínios: {', '.join(request.dominios)}\n",
        ]

        total = len(checklist)
        atendidos = len([c for c in checklist if c["status"] == "atendido"])
        pendentes = len([c for c in checklist if c["status"] == "pendente"])

        parts.append(f"Resumo: {atendidos}/{total} itens atendidos, {pendentes} pendentes\n")

        if conformidades:
            parts.append("✓ Conformidades verificadas:")
            for c in conformidades[:10]:
                parts.append(f"  • {c}")

        if gaps:
            parts.append("\n✗ GAPS de compliance identificados:")
            for g in gaps:
                parts.append(
                    f"  • [{g['severidade'].upper()}] {g['item']}"
                )
                parts.append(f"    Base legal: {g['artigo']}")
                parts.append(f"    Ação necessária: implementar antes de prosseguir")

        parts.append(
            "\nConclusão: "
            + (
                "Ação em conformidade com a legislação."
                if not gaps
                else "Ação requer correções de compliance antes de implementação."
            )
        )

        return "\n".join(parts)

    def _gerar_recomendacoes_compliance(
        self, gaps: list[dict], request: LegalRequest
    ) -> list[str]:
        recs = []

        for gap in gaps:
            recs.append(
                f"Implementar: {gap['item']} ({gap['artigo']})"
            )

        dominio_recs = {
            "dados_pessoais": [
                "Revisar Política de Privacidade",
                "Verificar Termos de Uso com cláusulas LGPD",
                "Treinar equipe sobre proteção de dados",
            ],
            "consumidor": [
                "Revisar material publicitário para transparência",
                "Verificar canais de atendimento ao consumidor",
            ],
            "trabalhista": [
                "Revisar contratos de trabalho",
                "Verificar regularidade junto ao e-Social",
            ],
        }

        for dominio in request.dominios:
            if dominio in dominio_recs:
                recs.extend(dominio_recs[dominio])

        return recs
