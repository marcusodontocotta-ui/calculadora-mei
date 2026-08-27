import pytest
from cupula.legal_gateway.models import LegalRequest


class TestLegislatorAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.legal.legislator import LegislatorAgent
        return LegislatorAgent()

    @pytest.mark.asyncio
    async def test_analyze_data_laws(self, agent):
        from cupula.legal_gateway.laws.database import LegalDB
        db = LegalDB()
        db._load_built_in_laws()

        request = LegalRequest(
            id="test-001",
            titulo="Coleta de dados de clientes",
            descricao="Sistema que coleta dados pessoais de clientes",
            dominios=["dados_pessoais"],
        )
        leis = await db.search("dados_pessoais", request.descricao)
        leis_por_dominio = {"dados_pessoais": leis}

        result = await agent.analyze(request, leis_por_dominio)
        assert "veredito" in result
        assert "parecer" in result
        assert result["veredito"] is not None


class TestComplianceAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.legal.compliance import ComplianceAgent
        return ComplianceAgent()

    @pytest.mark.asyncio
    async def test_analyze_lgpd(self, agent):
        from cupula.legal_gateway.laws.database import LegalDB
        db = LegalDB()
        db._load_built_in_laws()

        request = LegalRequest(
            id="test-002",
            titulo="App com dados pessoais",
            descricao="Aplicativo que coleta consentimento de titulares de dados pessoais",
            dominios=["dados_pessoais"],
        )
        leis = await db.search("dados_pessoais", request.descricao)

        result = await agent.analyze(request, {"dados_pessoais": leis})
        assert "veredito" in result
        assert "parecer" in result


class TestRiskLegalAgent:
    @pytest.fixture
    def agent(self):
        from cupula.agents.legal.risk import RiskLegalAgent
        return RiskLegalAgent()

    @pytest.mark.asyncio
    async def test_risk_assessment(self, agent):
        from cupula.legal_gateway.laws.database import LegalDB
        db = LegalDB()
        db._load_built_in_laws()

        request = LegalRequest(
            id="test-003",
            titulo="Sistema de alto risco",
            descricao="Sistema financeiro com dados bancários e tributários",
            dominios=["tributario", "dados_pessoais"],
        )
        leis_trib = await db.search("tributario")
        leis_dp = await db.search("dados_pessoais")

        result = await agent.analyze(request, {"tributario": leis_trib, "dados_pessoais": leis_dp})
        assert "veredito" in result
        assert "risco" in result
