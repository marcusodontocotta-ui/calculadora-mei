import pytest
from cupula.legal_gateway.models import LegalRequest


class TestLegalDB:
    @pytest.fixture
    def db(self):
        from cupula.legal_gateway.laws.database import LegalDB
        db = LegalDB()
        db._load_built_in_laws()
        return db

    @pytest.mark.asyncio
    async def test_count_laws(self, db):
        count = db._count_laws()
        assert count >= 15

    @pytest.mark.asyncio
    async def test_search_dados_pessoais(self, db):
        results = await db.search("dados_pessoais", "privacidade dados consentimento")
        assert len(results) > 0
        assert any("13.709/2018" in r.lei_numero for r in results)

    @pytest.mark.asyncio
    async def test_search_trabalhista(self, db):
        results = await db.search("trabalhista", "funcionário contrato")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_consumidor(self, db):
        results = await db.search("consumidor", "compra produto vício")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_empty_domain(self, db):
        results = await db.search("dominio_inexistente")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_domain_stats(self, db):
        stats = await db.get_domain_stats()
        assert "dados_pessoais" in stats
        assert stats["dados_pessoais"] >= 2
