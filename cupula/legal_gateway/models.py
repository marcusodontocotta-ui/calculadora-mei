import time
from typing import Any
from dataclasses import dataclass, field
from enum import Enum


class LegalDomain(Enum):
    DADOS_PESSOAIS = "dados_pessoais"
    TRABALHISTA = "trabalhista"
    TRIBUTARIO = "tributario"
    CIVIL = "civil"
    EMPRESARIAL = "empresarial"
    CONSUMIDOR = "consumidor"
    AMBIENTAL = "ambiental"
    DIGITAL = "digital"
    PROPRIEDADE_INTELECTUAL = "propriedade_intelectual"
    BANCARIO = "bancario"
    SAUDE = "saude"
    EDUCACAO = "educacao"
    CONCORRENCIA = "concorrencia"


class LegalSeverity(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4
    BLOQUEANTE = 5


class LegalVerdict(Enum):
    CONFORME = "CONFORME"
    NAO_CONFORME = "NAO_CONFORME"
    CONDICIONAL = "CONDICIONAL"
    REVISAO_NECESSARIA = "REVISAO_NECESSARIA"
    EM_ANALISE = "EM_ANALISE"


@dataclass
class LegalReference:
    lei_numero: str
    orgao: str
    titulo: str
    dominio: str
    ementa: str = ""
    data_vigencia: str = ""
    artigos_relevantes: list[str] = field(default_factory=list)
    palavras_chave: list[str] = field(default_factory=list)
    update_timestamp: float = 0.0


@dataclass
class LegalOpinion:
    id: str
    dominio: str
    titulo: str
    analise: str
    leis_aplicaveis: list[LegalReference]
    risco: LegalSeverity
    veredito: LegalVerdict
    parecer: str
    recomendacoes: list[str]
    confianca: float
    agente_responsavel: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LegalRequest:
    id: str
    titulo: str
    descricao: str
    dominios: list[str]
    contexto: dict[str, Any] = field(default_factory=dict)
    acao_proposta: str = ""
    dados_envolvidos: list[str] = field(default_factory=list)
    jurisdictions: list[str] = field(default_factory=lambda: ["brasil"])
    timestamp: float = field(default_factory=time.time)
