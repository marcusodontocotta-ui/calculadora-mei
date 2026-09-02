import asyncio
import json
import time
from datetime import datetime

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.core.message import DecisionRequest
from cupula.core.orchestrator import Orchestrator
from cupula.core.persist import persist_decision
from cupula.legal_gateway.gateway import LegalGateway
from cupula.legal_gateway.models import LegalRequest
from cupula.ai_gateway.gateway import AIGateway
from cupula.ai_gateway.capabilities import VisionAgent, CodeAgent, CreativeAgent
from cupula.agents.legal import (
    LegislatorAgent,
    ComplianceAgent,
    JurisprudenceAgent,
    RiskLegalAgent,
    RegulatoryAgent,
)
from cupula.agents.meta.self_improver import SelfImproverAgent
from cupula.agents.meta.auditor import AuditorAgent
from cupula.agents.meta.optimizer import OptimizerAgent
from cupula.agents.meta.analyst import AnalystAgent

logger = get_logger("app")


DOMAIN_KEYWORDS = {
    "dados_pessoais": ["dados pessoais", "privacidade", "lgpd", "consentimento", "perfil", "navegação", "navegacao"],
    "consumidor": ["consumidor", "compra", "venda", "produto", "serviço", "servico", "garantia"],
    "trabalhista": ["funcionário", "funcionario", "trabalho", "contrato", "salário", "salario", "jornada"],
    "empresarial": ["empresa", "sociedade", "faturamento", "lucro", "capital", "MEI"],
    "tributário": ["imposto", "tributo", "nf-e", "nota fiscal", "simples nacional"],
    "tributario": ["imposto", "tributo", "nf-e", "nota fiscal", "simples nacional"],
    "digital": ["digital", "internet", "e-commerce", "plataforma", "sistema", "software", "API", "api"],
    "propriedade_intelectual": ["patente", "marca", "autor", "copyright", "software"],
}


class CupulaApp:
    """Aplicação principal da Cúpula de Gestão Autônoma."""

    def __init__(self):
        self.settings = get_settings()
        self.orchestrator = Orchestrator()
        self.legal_gateway = LegalGateway(redis_url=self.settings.REDIS_URL)
        self.ai_gateway = AIGateway(redis_url=self.settings.REDIS_URL)
        self._report_count = 0
        self._start_time = time.time()
        self._decision_history: list[dict] = []

        self.meta_self_improver = SelfImproverAgent()
        self.meta_auditor = AuditorAgent()
        self.meta_optimizer = OptimizerAgent()
        self.meta_analyst = AnalystAgent()

        self.vision_agent: VisionAgent | None = None
        self.code_agent: CodeAgent | None = None
        self.creative_agent: CreativeAgent | None = None

    async def start(self):
        logger.info("Iniciando Cúpula de Gestão Autônoma...")

        await self.orchestrator.start()
        await self.legal_gateway.connect()

        self._register_legal_agents()

        try:
            await self.ai_gateway.connect()
            self.vision_agent = VisionAgent(self.ai_gateway)
            self.code_agent = CodeAgent(self.ai_gateway)
            self.creative_agent = CreativeAgent(self.ai_gateway)
            logger.info("AI Gateway e 3 capability agents (vision, code, creative) conectados")
        except Exception as e:
            logger.warning(f"Ai Gateway indisponível (funcionalidade limitada): {e}")

        logger.info("Cúpula iniciada com sucesso")

    async def stop(self):
        await self.orchestrator.stop()
        await self.legal_gateway.disconnect()
        try:
            await self.ai_gateway.disconnect()
        except Exception:
            pass

    def _register_legal_agents(self):
        self.legal_gateway.register_agent("legislator", LegislatorAgent())
        self.legal_gateway.register_agent("compliance", ComplianceAgent())
        self.legal_gateway.register_agent("jurisprudence", JurisprudenceAgent())
        self.legal_gateway.register_agent("risk_legal", RiskLegalAgent())
        self.legal_gateway.register_agent("regulatory", RegulatoryAgent())
        logger.info("5 agentes jurídicos registrados no Setor Jurídico")

    def _infer_domains(self, text: str) -> list[str]:
        text_lower = text.lower()
        detected = []
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                if domain not in detected:
                    detected.append(domain)
        return detected or ["digital"]

    async def process_decision(
        self,
        title: str,
        description: str,
        context: dict | None = None,
        constraints: list[str] | None = None,
        priority: int = 5,
        auto_legal: bool = True,
    ) -> dict:
        start = time.time()

        request = DecisionRequest(
            title=title,
            description=description,
            context=context or {},
            constraints=constraints or [],
            priority=priority,
        )

        decision_result = await self.orchestrator.submit_decision(request)

        full_text = f"{title} {description}"
        domains = self._infer_domains(full_text)

        legal_result = None
        if auto_legal and domains:
            try:
                legal_result = await self.legal_analysis(
                    titulo=title,
                    descricao=description,
                    dominios=domains,
                    acao_proposta=description[:500],
                )
            except Exception as e:
                logger.error(f"Erro na análise legal automática: {e}")
                legal_result = {"error": str(e)}

        elapsed = (time.time() - start) * 1000

        combined = {
            **decision_result,
            "legal_analysis": legal_result,
            "elapsed_ms": elapsed,
        }

        record = {
            "request_id": request.id,
            "title": title,
            "description": description,
            "domains": domains,
            "verdict": decision_result.get("verdict", "UNKNOWN"),
            "confidence": decision_result.get("confidence", 0),
            "decision_result": decision_result,
            "legal_verdict": (
                legal_result.get("opinion", {}).get("veredito", "N/A")
                if legal_result and "opinion" in legal_result
                else "N/A"
            ),
            "timestamp": time.time(),
            "elapsed_ms": elapsed,
        }
        persist_decision(record)

        self._decision_history.append(record)

        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]

        return combined

    async def legal_analysis(
        self,
        titulo: str,
        descricao: str,
        dominios: list[str],
        **kwargs,
    ) -> dict:
        request = LegalRequest(
            id=f"legal_{int(time.time())}_{hash(titulo) % 10000}",
            titulo=titulo,
            descricao=descricao,
            dominios=dominios,
            acao_proposta=kwargs.get("acao_proposta", ""),
            dados_envolvidos=kwargs.get("dados_envolvidos", []),
        )
        return await self.legal_gateway.analyze(request)

    async def run_meta_analysis(self) -> dict:
        """Executa todos os meta-agentes e retorna análise consolidada."""
        system_status = await self.orchestrator.get_system_status()
        legal_stats = await self.legal_gateway.get_stats()
        batch_stats = await self.orchestrator.batch.get_stats()
        conferidor_stats = await self.orchestrator.conferidor.get_stats()
        health = await self.orchestrator.metrics.get_health()

        reputation_lb = await self.orchestrator.reputation.get_leaderboard(10)
        cb_status = await self.orchestrator.circuit_breaker.get_all_status()

        metrics_for_meta = {
            "health": health,
            "active_agents": {"count": health.get("active_agents", 0)},
            "latency_decision": await self.orchestrator.metrics.get_latency("agent_response"),
        }

        improving = await self.meta_self_improver.analyze_system(
            metrics=metrics_for_meta,
            reputation_data=reputation_lb,
            circuit_data=cb_status,
            conferidor_stats=conferidor_stats,
        )

        audit = await self.meta_auditor.generate_report()

        optimizing = await self.meta_optimizer.analyze_performance(
            metrics=metrics_for_meta,
            batch_stats=batch_stats,
            conferidor_stats=conferidor_stats,
        )

        analyzing = await self.meta_analyst.analyze_decisions(
            recent_decisions=self._decision_history[-50:]
        )

        return {
            "self_improver": improving,
            "auditor": audit,
            "optimizer": optimizing,
            "analyst": analyzing,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_health(self) -> dict:
        uptime = time.time() - self._start_time
        try:
            redis_status = "connected"
            await self.orchestrator.bus._redis.ping()
        except Exception:
            redis_status = "error"

        legal_db_laws = 0
        if self.legal_gateway._legal_db:
            legal_db_laws = self.legal_gateway._legal_db._count_laws()

        legal_stats = await self.legal_gateway.get_stats()

        return {
            "status": "healthy" if redis_status == "connected" else "degraded",
            "version": self.settings.VERSION,
            "uptime_seconds": round(uptime, 1),
            "redis": redis_status,
            "agents_registered": len(self.orchestrator._agents),
            "legal_agents_registered": len(self.legal_gateway._agents),
            "legal_db_laws": legal_db_laws,
            "legal_analyses": legal_stats.get("total_analises", 0),
            "decisions_processed": len(self._decision_history),
            "ai_gateway": "connected" if self.ai_gateway._http_client else "disconnected",
            "ai_capabilities": sum(
                1 for a in [self.vision_agent, self.code_agent, self.creative_agent]
                if a is not None
            ),
        }

    async def generate_report(self) -> dict:
        self._report_count += 1

        system_status = await self.orchestrator.get_system_status()
        legal_stats = await self.legal_gateway.get_stats()
        legal_alerts = await self.legal_gateway.get_alerts(10)
        health = await self.orchestrator.metrics.get_health()

        report = {
            "report_id": f"report_{self._report_count}",
            "generated_at": datetime.now().isoformat(),
            "system": {
                "status": "operational",
                "agents_registered": system_status.get("agents_registered", 0),
                "uptime": "ativo",
                "metrics": health,
            },
            "legal_department": {
                "total_analyses": legal_stats.get("total_analises", 0),
                "verdicts": {
                    k.replace("veredito:", ""): v
                    for k, v in legal_stats.items()
                    if k.startswith("veredito:")
                },
                "risks": {
                    k.replace("risco:", ""): v
                    for k, v in legal_stats.items()
                    if k.startswith("risco:")
                },
                "domains": {
                    k.replace("dominio:", ""): v
                    for k, v in legal_stats.items()
                    if k.startswith("dominio:")
                },
            },
            "decision_history": self._decision_history[-20:],
            "alerts": legal_alerts,
        }

        report_path = self.settings.LOGS_DIR / f"report_{self._report_count}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Relatório #{self._report_count} gerado: {report_path}")
        return report

    # ── AI Capabilities ────────────────────────────────────────────────────

    def _require_ai(self, agent_name: str, agent_obj):
        if agent_obj is None:
            raise RuntimeError(
                f"AI Gateway não conectado. {agent_name} indisponível. "
                "Verifique as credenciais de API."
            )
        return agent_obj

    async def ai_code_generate(
        self,
        description: str,
        language: str = "python",
        framework: str = "",
        style: str = "",
        constraints: list[str] | None = None,
    ) -> dict:
        agent = self._require_ai("CodeAgent", self.code_agent)
        return await agent.generate_code(
            description=description,
            language=language,
            framework=framework,
            style=style,
            constraints=constraints,
        )

    async def ai_code_review(self, code: str, language: str = "python") -> dict:
        agent = self._require_ai("CodeAgent", self.code_agent)
        return await agent.review_code(code=code, language=language)

    async def ai_code_debug(self, code: str, error: str, language: str = "python") -> dict:
        agent = self._require_ai("CodeAgent", self.code_agent)
        return await agent.debug_error(code=code, error=error, language=language)

    async def ai_generate_image(
        self,
        prompt: str,
        style: str = "natural",
        size: str = "1024x1024",
        quality: str = "hd",
        variations: int = 1,
    ) -> dict:
        agent = self._require_ai("CreativeAgent", self.creative_agent)
        return await agent.generate_image(
            prompt=prompt, style=style, size=size, quality=quality, variations=variations,
        )

    async def ai_create_copy(self, brief: str, product: str, audience: str) -> dict:
        agent = self._require_ai("CreativeAgent", self.creative_agent)
        return await agent.create_copy(product=product, audience=audience)

    async def ai_brainstorm(self, topic: str, context: str = "", count: int = 5) -> dict:
        agent = self._require_ai("CreativeAgent", self.creative_agent)
        return await agent.brainstorm(topic=topic, count=count)

    async def ai_vision_screenshot(self, image_url: str, context: str = "") -> dict:
        agent = self._require_ai("VisionAgent", self.vision_agent)
        return await agent.analyze_screenshot(image_url=image_url, context=context)

    async def ai_vision_ocr(self, image_url: str) -> dict:
        agent = self._require_ai("VisionAgent", self.vision_agent)
        return await agent.ocr_image(image_url=image_url)

    async def ai_vision_compare(self, image_url_a: str, image_url_b: str) -> dict:
        agent = self._require_ai("VisionAgent", self.vision_agent)
        return await agent.compare_versions(image_url_a=image_url_a, image_url_b=image_url_b)

    async def ai_capabilities_list(self) -> dict:
        result = {"ai_gateway": "connected" if self.ai_gateway._http_client else "disconnected"}
        caps = {"vision": self.vision_agent, "code": self.code_agent, "creative": self.creative_agent}
        for name, agent in caps.items():
            if agent:
                result[name] = agent.get_stats()
            else:
                result[name] = {"status": "unavailable"}
        return result
