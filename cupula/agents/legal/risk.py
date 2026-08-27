from typing import Any
from cupula.core.logger import get_logger
from cupula.legal_gateway.models import LegalRequest, LegalSeverity, LegalVerdict

logger = get_logger("legal.risk")


class RiskLegalAgent:
    """Agente de Avaliação de Risco Jurídico."""

    def __init__(self):
        self.agent_id = "risk_legal"

    async def analyze(
        self,
        request: LegalRequest,
        leis_por_dominio: dict,
    ) -> dict[str, Any]:
        logger.info(f"Avaliando risco jurídico: {request.titulo}")

        riscos = []
        multa_total = 0.0

        riscos_multa = {
            "dados_pessoais": {"base": 2000, "max_por_titular": 50000},
            "consumidor": {"base": 1000, "max_por_consumidor": 10000},
            "trabalhista": {"base": 5000, "max_por_funcionario": 50000},
            "ambiental": {"base": 10000, "max": 500000},
            "tributario": {"base": 5000, "max": 1000000},
        }

        for dominio in request.dominios:
            risco_cfg = riscos_multa.get(dominio, {"base": 1000})
            riscos.append({
                "dominio": dominio,
                "tipo": "multa",
                "valor_base": risco_cfg["base"],
                "descricao": f"Multa por infração em {dominio}",
                "severidade": "alta" if risco_cfg["base"] > 5000 else "media",
            })
            multa_total += risco_cfg["base"]

        dados_env = request.dados_envolvidos
        if dados_env:
            riscos.append({
                "dominio": "geral",
                "tipo": "reputacional",
                "descricao": f"Dados envolvidos: {', '.join(dados_env)}",
                "severidade": "alta",
            })

        texto = (request.descricao + " " + request.acao_proposta).lower()
        if any(p in texto for p in ["delete", "remover", "destruir"]):
            riscos.append({
                "dominio": "operacional",
                "tipo": "perda_dados",
                "descricao": "Operação destrutiva pode causar perda irreversível",
                "severidade": "critica",
            })
            multa_total += 100000

        if any(p in texto for p in ["publico", "internet", "web", "api"]):
            riscos.append({
                "dominio": "digital",
                "tipo": "exposição",
                "descricao": "Exposição pública aumenta risco de incidentes",
                "severidade": "media",
            })

        max_sev = self._get_max_severity(riscos)

        if max_sev == "critica":
            veredito = LegalVerdict.NAO_CONFORME
            risco_nivel = LegalSeverity.CRITICA
        elif max_sev == "alta":
            veredito = LegalVerdict.CONDICIONAL
            risco_nivel = LegalSeverity.ALTA
        elif max_sev == "media":
            veredito = LegalVerdict.CONDICIONAL
            risco_nivel = LegalSeverity.MEDIA
        else:
            veredito = LegalVerdict.CONFORME
            risco_nivel = LegalSeverity.BAIXA

        parecer = self._gerar_parecer(riscos, multa_total, request)

        return {
            "veredito": veredito,
            "risco": risco_nivel,
            "parecer": parecer,
            "riscos": riscos,
            "multa_estimada": multa_total,
            "recomendacoes": self._recomendacoes(riscos, request),
        }

    def _get_max_severity(self, riscos: list[dict]) -> str:
        ordem = {"baixa": 0, "media": 1, "alta": 2, "critica": 3}
        max_s = 0
        for r in riscos:
            s = ordem.get(r.get("severidade", "baixa"), 0)
            if s > max_s:
                max_s = s
        return {0: "baixa", 1: "media", 2: "alta", 3: "critica"}.get(max_s, "baixa")

    def _gerar_parecer(self, riscos, multa, request):
        parts = [
            "=== PARECER DE RISCO JURÍDICO ===\n",
            f"Ação: {request.titulo}",
            f"Riscos identificados: {len(riscos)}",
            f"Multa estimada base: R$ {multa:,.2f}\n",
        ]
        for r in riscos:
            parts.append(
                f"• [{r['severidade'].upper()}] {r['tipo']} ({r['dominio']}): {r['descricao']}"
            )
        parts.append(f"\nExposição financeira máxima estimada: R$ {multa:,.2f}")
        return "\n".join(parts)

    def _recomendacoes(self, riscos, request):
        recs = []
        if any(r["severidade"] == "critica" for r in riscos):
            recs.append("SUSPENDER ação até mitigação de riscos críticos")
        if any(r["tipo"] == "multa" and r["valor_base"] > 5000 for r in riscos):
            recs.append("Consultar advogado especializado antes de prosseguir")
        if request.dados_envolvidos:
            recs.append("Implementar criptografia e acesso restrito aos dados")
        recs.append("Documentar todas as decisões para eventual defesa")
        return recs
