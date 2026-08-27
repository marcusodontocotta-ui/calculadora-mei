import pytest
from cupula.core.message import DecisionRequest, DecisionResponse


class TestSentinelAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.builtin.sentinel.agent import SentinelAgent
        return SentinelAgent()

    @pytest.mark.asyncio
    async def test_analyze_with_security_keywords(self, agent):
        req = DecisionRequest(
            title="Criptografia de dados",
            description="Sistema com autenticação e dados sensíveis em sandbox isolado",
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "sentinel"
        assert resp.verdict in ["APROVADO", "CONDICIONAL"]
        assert len(resp.risks) > 0
        assert resp.confidence > 0.5

    @pytest.mark.asyncio
    async def test_analyze_clean_project(self, agent):
        req = DecisionRequest(
            title="App de receitas",
            description="App simples para listar receitas de culinária",
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "sentinel"
        assert resp.verdict == "APROVADO"


class TestNexusAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.builtin.nexus.agent import NexusAgent
        return NexusAgent()

    @pytest.mark.asyncio
    async def test_analyze_with_tech_stack(self, agent):
        req = DecisionRequest(
            title="API REST com Python",
            description="Criar API FastAPI com PostgreSQL e Docker",
            context={"stack": ["python", "docker"]},
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "nexus"
        assert resp.verdict in ["APROVADO", "CONDICIONAL"]
        assert resp.confidence > 0.5

    @pytest.mark.asyncio
    async def test_analyze_generic(self, agent):
        req = DecisionRequest(
            title="Sistema simples",
            description="Sistema básico sem tecnologias especificadas",
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "nexus"


class TestVortexAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.builtin.vortex.agent import VortexAgent
        return VortexAgent()

    @pytest.mark.asyncio
    async def test_analyze_business(self, agent):
        req = DecisionRequest(
            title="Plataforma SaaS B2B",
            description="Sistema de monetização com assinatura e análise de mercado",
            context={"orcamento": 50000},
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "vortex"
        assert resp.verdict in ["APROVADO", "CONDICIONAL"]
        assert len(resp.risks) > 0

    @pytest.mark.asyncio
    async def test_analyze_no_business_context(self, agent):
        req = DecisionRequest(
            title="Projeto interno",
            description="Ferramenta para uso interno da equipe",
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "vortex"
        assert len(resp.recommendations) > 0


class TestApoloAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.builtin.apolo.agent import ApoloAgent
        return ApoloAgent()

    @pytest.mark.asyncio
    async def test_analyze_simple(self, agent):
        req = DecisionRequest(
            title="Tarefa simples",
            description="Pequena correção de bug",
            priority=3,
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "apolo"
        assert resp.verdict == "APROVADO"

    @pytest.mark.asyncio
    async def test_analyze_complex(self, agent):
        req = DecisionRequest(
            title="Sistema complexo multi-tenant com IA",
            description="Sistema multi-tenant com Docker, IA, PostgreSQL, e multiples APIs externas " * 3,
            constraints=["LGPD", "SLA 99.99%", "Deploy em 2 semanas"],
            priority=10,
            context={"fase1": "backend", "fase2": "frontend", "fase3": "infra", "fase4": "ml", "fase5": "testing", "fase6": "deploy"},
        )
        resp = await agent.analyze(req)
        assert resp.agent_role == "apolo"
        assert len(resp.risks) > 0
