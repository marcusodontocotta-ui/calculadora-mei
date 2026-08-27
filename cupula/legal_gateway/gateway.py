import json
import time
from typing import Any

import redis.asyncio as aioredis

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.legal_gateway.models import (
    LegalSeverity,
    LegalVerdict,
    LegalReference,
    LegalOpinion,
    LegalRequest,
)

logger = get_logger("legal_gateway")


class LegalGateway:
    """Diretor do Setor Jurídico.

    Coordena todos os agentes jurídicos:
    - LegislatorAgent: interpreta leis e cita numeração
    - ComplianceAgent: verifica conformidade
    - JurisprudenceAgent: analisa jurisprudência
    - RiskLegalAgent: avalia risco jurídico
    - RegulatoryAgent: monitora mudanças regulatórias

    Fluxo:
    1. Recebe request jurídico
    2. Identifica domínios do direito envolvidos
    3. Distribui para agentes especializados
    4. Consolida pareceres
    5. Emite parecer jurídico unificado com leis citadas
    """

    OPINIONS_PREFIX = "cupula:legal:opinions:"
    REQUESTS_PREFIX = "cupula:legal:requests:"
    ALERTS_KEY = "cupula:legal:alerts"
    STATS_KEY = "cupula:legal:stats"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._agents: dict[str, Any] = {}
        self._legal_db = None

    async def connect(self):
        from cupula.legal_gateway.laws.database import LegalDB

        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=30,
        )
        await self._redis.ping()
        self._legal_db = LegalDB(self._redis)
        await self._legal_db.init()
        logger.info("LegalGateway conectado")

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    def register_agent(self, agent_id: str, agent: Any):
        self._agents[agent_id] = agent
        logger.info(f"Agente jurídico registrado: {agent_id}")

    async def analyze(self, request: LegalRequest) -> dict[str, Any]:
        """Análise jurídica completa de uma ação/proposta."""
        start = time.time()

        logger.info(
            f"Análise jurídica: [{request.id}] {request.titulo} "
            f"(domínios: {', '.join(request.dominios)})"
        )

        leis_por_dominio = {}
        for dominio in request.dominios:
            leis = await self._legal_db.search(dominio, request.descricao)
            leis_por_dominio[dominio] = leis

        agent_results = {}
        for agent_id, agent in self._agents.items():
            try:
                result = await agent.analyze(request, leis_por_dominio)
                agent_results[agent_id] = result
            except Exception as e:
                logger.error(f"Erro no agente {agent_id}: {e}")
                agent_results[agent_id] = {"error": str(e)}

        opinion = self._consolidate(request, agent_results, leis_por_dominio)

        await self._save_opinion(opinion)
        await self._update_stats(request, opinion)

        if opinion.risco in [LegalSeverity.CRITICA, LegalSeverity.BLOQUEANTE]:
            await self._create_alert(request, opinion)

        elapsed = (time.time() - start) * 1000

        return {
            "request_id": request.id,
            "opinion": {
                "veredito": opinion.veredito.value,
                "risco": opinion.risco.name,
                "parecer": opinion.parecer,
                "analise": opinion.analise,
                "leis_aplicaveis": [
                    {
                        "lei": l.lei_numero,
                        "orgao": l.orgao,
                        "titulo": l.titulo,
                        "ementa": l.ementa,
                        "artigos": l.artigos_relevantes,
                    }
                    for l in opinion.leis_aplicaveis
                ],
                "recomendacoes": opinion.recomendacoes,
                "confianca": opinion.confianca,
            },
            "agentes_consultados": list(agent_results.keys()),
            "tempo_analise_ms": elapsed,
        }

    def _consolidate(
        self,
        request: LegalRequest,
        agent_results: dict,
        leis_por_dominio: dict,
    ) -> LegalOpinion:
        all_leis = []
        for leis in leis_por_dominio.values():
            all_leis.extend(leis)

        unique_leis = []
        seen = set()
        for lei in all_leis:
            if lei.lei_numero not in seen:
                seen.add(lei.lei_numero)
                unique_leis.append(lei)

        risks = []
        all_recs = []
        verdicts = []

        for agent_id, result in agent_results.items():
            if "error" in result:
                continue

            if "risco" in result:
                risks.append(result["risco"])
            if "recomendacoes" in result:
                all_recs.extend(result["recomendacoes"])
            if "veredito" in result:
                verdicts.append(result["veredito"])

        if risks:
            max_risk = max(risks, key=lambda x: x.value if isinstance(x, LegalSeverity) else x)
        else:
            max_risk = LegalSeverity.BAIXA

        if verdicts:
            if all(v == LegalVerdict.CONFORME for v in verdicts):
                final_verdict = LegalVerdict.CONFORME
            elif any(v == LegalVerdict.NAO_CONFORME for v in verdicts):
                final_verdict = LegalVerdict.NAO_CONFORME
            elif any(v == LegalVerdict.CONDICIONAL for v in verdicts):
                final_verdict = LegalVerdict.CONDICIONAL
            else:
                final_verdict = LegalVerdict.REVISAO_NECESSARIA
        else:
            final_verdict = LegalVerdict.REVISAO_NECESSARIA

        parecer_parts = [f"PARECER JURÍDICO - {request.titulo}\n"]
        parecer_parts.append(f"Domínios analisados: {', '.join(request.dominios)}\n")

        parecer_parts.append("LEIS APLICÁVEIS:")
        for lei in unique_leis[:10]:
            parecer_parts.append(f"  • Lei nº {lei.lei_numero} ({lei.orgao})")
            parecer_parts.append(f"    {lei.titulo}")
            if lei.ementa:
                parecer_parts.append(f"    Ementa: {lei.ementa[:200]}")
            if lei.artigos_relevantes:
                parecer_parts.append(f"    Artigos: {', '.join(lei.artigos_relevantes)}")

        parecer_parts.append(f"\nVEREDITO: {final_verdict.value}")
        parecer_parts.append(f"RISCO: {max_risk.name}")

        for agent_id, result in agent_results.items():
            if "error" not in result and "parecer" in result:
                parecer_parts.append(f"\n--- PARECER {agent_id.upper()} ---")
                parecer_parts.append(result["parecer"])

        unique_recs = list(dict.fromkeys(all_recs))
        if unique_recs_parts := [f"  {i+1}. {r}" for i, r in enumerate(unique_recs[:15])]:
            parecer_parts.append("\nRECOMENDAÇÕES:")
            parecer_parts.extend(unique_recs_parts)

        parecer = "\n".join(parecer_parts)

        agent_count = len([r for r in agent_results.values() if "error" not in r])
        confidence = min(0.95, 0.5 + (agent_count * 0.1) + (len(unique_leis) * 0.05))

        return LegalOpinion(
            id=f"opinion_{request.id}",
            dominio=", ".join(request.dominios),
            titulo=request.titulo,
            analise=parecer,
            leis_aplicaveis=unique_leis,
            risco=max_risk,
            veredito=final_verdict,
            parecer=parecer,
            recomendacoes=unique_recs[:20],
            confianca=confidence,
            agente_responsavel="legal_gateway",
        )

    async def _save_opinion(self, opinion: LegalOpinion):
        if self._redis:
            data = json.dumps({
                "id": opinion.id,
                "dominio": opinion.dominio,
                "titulo": opinion.titulo,
                "veredito": opinion.veredito.value,
                "risco": opinion.risco.value,
                "confianca": opinion.confianca,
                "leis": [l.lei_numero for l in opinion.leis_aplicaveis],
                "timestamp": opinion.timestamp,
            }, ensure_ascii=False)
            await self._redis.set(f"{self.OPINIONS_PREFIX}{opinion.id}", data)
            await self._redis.lpush(
                "cupula:legal:opinions:history", opinion.id
            )

    async def _update_stats(self, request: LegalRequest, opinion: LegalOpinion):
        if self._redis:
            await self._redis.hincrby(self.STATS_KEY, "total_analises", 1)
            await self._redis.hincrby(
                self.STATS_KEY, f"veredito:{opinion.veredito.value}", 1
            )
            await self._redis.hincrby(
                self.STATS_KEY, f"risco:{opinion.risco.name}", 1
            )
            for dominio in request.dominios:
                await self._redis.hincrby(
                    self.STATS_KEY, f"dominio:{dominio}", 1
                )

    async def _create_alert(self, request: LegalRequest, opinion: LegalOpinion):
        alert = {
            "request_id": request.id,
            "titulo": request.titulo,
            "risco": opinion.risco.name,
            "veredito": opinion.veredito.value,
            "leis": [l.lei_numero for l in opinion.leis_aplicaveis[:5]],
            "timestamp": time.time(),
        }
        if self._redis:
            await self._redis.lpush(self.ALERTS_KEY, json.dumps(alert))
            await self._redis.ltrim(self.ALERTS_KEY, 0, 999)

    async def get_stats(self) -> dict:
        if self._redis:
            raw = await self._redis.hgetall(self.STATS_KEY)
            return {k: int(v) for k, v in raw.items()} if raw else {}
        return {}

    async def get_alerts(self, limit: int = 20) -> list[dict]:
        if self._redis:
            entries = await self._redis.lrange(self.ALERTS_KEY, 0, limit - 1)
            return [json.loads(e) for e in entries]
        return []

    async def get_opinion(self, opinion_id: str) -> dict | None:
        if self._redis:
            data = await self._redis.get(f"{self.OPINIONS_PREFIX}{opinion_id}")
            return json.loads(data) if data else None
        return None
