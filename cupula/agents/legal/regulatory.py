import time
from typing import Any
from cupula.core.logger import get_logger
from cupula.legal_gateway.models import LegalRequest, LegalSeverity, LegalVerdict

logger = get_logger("legal.regulatory")


class RegulatoryAgent:
    """Agente Monitor de Mudanças Regulatórias."""

    RECENT_CHANGES = [
        {"lei": "15.182/2024", "dominio": "trabalhista", "assunto": "Trabalho intermitente", "impacto": "medio"},
        {"lei": "14.611/2023", "dominio": "trabalhista", "assunto": "Igualdade salarial", "impacto": "medio"},
        {"lei": "14.195/2021", "dominio": "empresarial", "assunto": "MEI e empresas", "impacto": "alto"},
        {"lei": "14.181/2021", "dominio": "consumidor", "assunto": "Crédito responsável", "impacto": "medio"},
        {"lei": "14.063/2020", "dominio": "digital", "assunto": "Assinatura eletrônica", "impacto": "alto"},
    ]

    def __init__(self):
        self.agent_id = "regulatory"

    async def analyze(
        self,
        request: LegalRequest,
        leis_por_dominio: dict,
    ) -> dict[str, Any]:
        logger.info(f"Verificando mudanças regulatórias: {request.titulo}")

        alertas = []
        for change in self.RECENT_CHANGES:
            if change["dominio"] in request.dominios:
                alertas.append({
                    "lei": change["lei"],
                    "assunto": change["assunto"],
                    "impacto": change["impacto"],
                    "descricao": f"Lei {change['lei']} ({change['assunto']}) em vigor",
                })

        texto = (request.descricao + " " + request.acao_proposta).lower()
        if "ia" in texto or "inteligencia artificial" in texto or "algoritmo" in texto:
            alertas.append({
                "lei": "Em tramitação",
                "assunto": "Regulamentação de IA",
                "impacto": "alto",
                "descricao": "PL 2338/2023 - Marco Legal da IA em tramitação no Congresso",
            })

        if "criptomoeda" in texto or "blockchain" in texto or "web3" in texto:
            alertas.append({
                "lei": "PL 4.522/2023",
                "assunto": "Regulamentação de criptoativos",
                "impacto": "alto",
                "descricao": "Regulamentação de ativos virtuais em análise",
            })

        has_high = any(a["impacto"] == "alto" for a in alertas)

        if has_high:
            veredito = LegalVerdict.CONDICIONAL
            risco = LegalSeverity.MEDIA
        elif alertas:
            veredito = LegalVerdict.CONFORME
            risco = LegalSeverity.BAIXA
        else:
            veredito = LegalVerdict.CONFORME
            risco = LegalSeverity.BAIXA

        parecer = self._gerar_parecer(alertas, request)

        return {
            "veredito": veredito,
            "risco": risco,
            "parecer": parecer,
            "alertas": alertas,
            "recomendacoes": [
                "Monitorar mudanças legislativas periodicamente",
                "Verificar novas regulamentações antes de implementação",
            ] if alertas else ["Nenhuma mudança regulatória crítica identificada"],
        }

    def _gerar_parecer(self, alertas, request):
        parts = [
            "=== PARECER REGULATÓRIO ===\n",
            f"Análise: {request.titulo}",
            f"Alertas regulatórios: {len(alertas)}\n",
        ]
        if alertas:
            for a in alertas:
                parts.append(f"• [{a['impacto'].upper()}] {a['lei']}: {a['descricao']}")
        else:
            parts.append("Nenhuma mudança regulatória relevante identificada.")
        return "\n".join(parts)
