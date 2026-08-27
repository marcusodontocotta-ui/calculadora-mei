import pytest
from cupula.legal_gateway.models import (
    LegalReference,
    LegalRequest,
    LegalSeverity,
    LegalVerdict,
    LegalDomain,
)


def test_legal_reference():
    ref = LegalReference(
        lei_numero="13.709/2018",
        orgao="Congresso Nacional",
        titulo="LGPD",
        dominio="dados_pessoais",
    )
    assert ref.lei_numero == "13.709/2018"
    assert ref.dominio == "dados_pessoais"


def test_legal_request():
    req = LegalRequest(
        id="test-001",
        titulo="Teste",
        descricao="Descricao do teste",
        dominios=["dados_pessoais"],
    )
    assert req.id == "test-001"
    assert len(req.dominios) == 1
    assert req.jurisdictions == ["brasil"]


def test_legal_severity_ordering():
    assert LegalSeverity.BAIXA.value < LegalSeverity.MEDIA.value
    assert LegalSeverity.MEDIA.value < LegalSeverity.ALTA.value
    assert LegalSeverity.ALTA.value < LegalSeverity.CRITICA.value
    assert LegalSeverity.CRITICA.value < LegalSeverity.BLOQUEANTE.value


def test_legal_verdict_values():
    assert LegalVerdict.CONFORME.value == "CONFORME"
    assert LegalVerdict.NAO_CONFORME.value == "NAO_CONFORME"
    assert LegalVerdict.CONDICIONAL.value == "CONDICIONAL"
    assert LegalVerdict.REVISAO_NECESSARIA.value == "REVISAO_NECESSARIA"


def test_legal_domain_values():
    assert LegalDomain.DADOS_PESSOAIS.value == "dados_pessoais"
    assert LegalDomain.TRABALHISTA.value == "trabalhista"
    assert LegalDomain.DIGITAL.value == "digital"
