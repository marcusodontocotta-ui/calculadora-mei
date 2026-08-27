import json
import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.legal_gateway.models import LegalReference

logger = get_logger("legal_db")


class LegalDB:
    """Base de dados de leis vigentes por domínio.

    Contém leis brasileiras organizadas por área do direito.
    Atualizada automaticamente via RegulatoryAgent.
    """

    LAWS_PREFIX = "cupula:legal:db:"
    DOMAINS_KEY = "cupula:legal:db:domains"

    def __init__(self, redis=None):
        self._redis = redis
        self._local_db: dict[str, list[LegalReference]] = {}

    async def init(self):
        """Inicializa com leis fundamentais."""
        self._load_built_in_laws()
        if self._redis:
            await self._persist_to_redis()
        logger.info(f"LegalDB inicializada com {self._count_laws()} leis")

    def _load_built_in_laws(self):
        laws_dados_pessoais = [
            LegalReference(
                lei_numero="13.709/2018",
                orgao="Congresso Nacional",
                titulo="Lei Geral de Protecao de Dados Pessoais (LGPD)",
                dominio="dados_pessoais",
                ementa="Regula o tratamento de dados pessoais, inclusive nos meios digitais, por pessoa natural ou juridica de direito publico ou privado.",
                artigos_relevantes=["7", "8", "9", "11", "18", "37", "41", "46", "48", "50"],
                palavras_chave=["dados pessoais", "privacidade", "consentimento", "tratamento", "titular", "encarregado"],
            ),
            LegalReference(
                lei_numero="12.965/2014",
                orgao="Congresso Nacional",
                titulo="Marco Civil da Internet no Brasil",
                dominio="dados_pessoais",
                ementa="Estabelece principios, garantias e direitos dos usuarios da Internet no Brasil.",
                artigos_relevantes=["2", "3", "7", "8", "9", "10"],
                palavras_chave=["internet", "neutralidade", "privacidade", "liberdade de expressao"],
            ),
            LegalReference(
                lei_numero="13.846/2019",
                orgao="Congresso Nacional",
                titulo="Lei do Cadastro Positivo",
                dominio="dados_pessoais",
                ementa="Dispoe sobre o tratamento de dados pessoais pelo Banco Central do Brasil.",
                artigos_relevantes=["3", "4", "5"],
                palavras_chave=["cadastro", "score", "crédito", "bureau"],
            ),
        ]

        laws_trabalhistas = [
            LegalReference(
                lei_numero="8.112/1990",
                orgao="Congresso Nacional",
                titulo="Regime Juridico dos Servidores Publicos Civis da Uniao",
                dominio="trabalhista",
                ementa="Dispoe sobre o regime juridico dos servidores publicos civis da Uniao.",
                artigos_relevantes=["2", "116", "117", "132"],
                palavras_chave=["servidor", "publico", "direitos", "deveres", "regime"],
            ),
            LegalReference(
                lei_numero="14.442/2022",
                orgao="Congresso Nacional",
                titulo="Trabalho Domestico - Jornada 12x36",
                dominio="trabalhista",
                ementa="Dispoe sobre a regulamentacao da jornada 12x36.",
                artigos_relevantes=["1", "2", "3"],
                palavras_chave=["jornada", "12x36", "domestico", "trabalho"],
            ),
            LegalReference(
                lei_numero="14.611/2023",
                orgao="Congresso Nacional",
                titulo="Igualdade Salarial e Remuneratoria",
                dominio="trabalhista",
                ementa="Dispoe sobre a igualdade salarial e remuneratoria.",
                artigos_relevantes=["1", "2", "3", "4"],
                palavras_chave=["igualdade", "salario", "genero", "remuneracao"],
            ),
            LegalReference(
                lei_numero="15.182/2024",
                orgao="Congresso Nacional",
                titulo="Trabalho Intermitente",
                dominio="trabalhista",
                ementa="Dispoe sobre o contrato de trabalho intermitente.",
                artigos_relevantes=["1", "2", "3", "4"],
                palavras_chave=["intermitente", "contrato", "trabalho", "flexivel"],
            ),
        ]

        laws_empresariais = [
            LegalReference(
                lei_numero="6.404/1976",
                orgao="Congresso Nacional",
                titulo="Lei das Sociedades por Acoes",
                dominio="empresarial",
                ementa="Dispoe sobre as Sociedades por Acoes.",
                artigos_relevantes=["1", "2", "100", "105"],
                palavras_chave=["sociedade", "acoes", "balanco", "assembleia"],
            ),
            LegalReference(
                lei_numero="14.195/2021",
                orgao="Congresso Nacional",
                titulo="Lei das Microempresas e Empresas de Pequeno Porte",
                dominio="empresarial",
                ementa="Dispoe sobre oregistro de empresas e sobre o Microempreendedor Individual (MEI).",
                artigos_relevantes=["1", "2", "3", "18-A"],
                palavras_chave=["MEI", "ME", "EPP", "simples", "nacional"],
            ),
            LegalReference(
                lei_numero="11.101/2005",
                orgao="Congresso Nacional",
                titulo="Lei de Recuperacao Judicial e Extrajudicial",
                dominio="empresarial",
                ementa="Dispoe sobre a recuperacao judicial, extrajudicial e a falencia do empresario.",
                artigos_relevantes=["2", "3", "47", "49", "66", "94"],
                palavras_chave=["recuperacao", "judicial", "falencia", "insolvencia"],
            ),
        ]

        laws_consumidor = [
            LegalReference(
                lei_numero="8.078/1990",
                orgao="Congresso Nacional",
                titulo="Codigo de Defesa do Consumidor",
                dominio="consumidor",
                ementa="Dispoe sobre a protecao do consumidor.",
                artigos_relevantes=["1", "2", "6", "12", "14", "18", "26", "39", "42", "49"],
                palavras_chave=["consumidor", "fornecedor", "produto", "servico", "vicio", "dano"],
            ),
            LegalReference(
                lei_numero="14.181/2021",
                orgao="Congresso Nacional",
                titulo="Credito Responsavel",
                dominio="consumidor",
                ementa="Dispoe sobre o credito responsavel ao consumidor.",
                artigos_relevantes=["1", "2", "3"],
                palavras_chave=["credito", "responsavel", "consumidor", "juros"],
            ),
        ]

        laws_digital = [
            LegalReference(
                lei_numero="14.063/2020",
                orgao="Congresso Nacional",
                titulo="Assinatura Eletronica",
                dominio="digital",
                ementa="Dispoe sobre o uso da assinatura eletronica.",
                artigos_relevantes=["1", "2", "3", "4", "5"],
                palavras_chave=["assinatura", "eletronica", "digital", "certificado"],
            ),
            LegalReference(
                lei_numero="14.133/2021",
                orgao="Congresso Nacional",
                titulo="Nova Lei de Licitacoes",
                dominio="digital",
                ementa="Dispoe sobre licitacoes e contratos administrativos.",
                artigos_relevantes=["28", "31", "49", "75"],
                palavras_chave=["licitacao", "contrato", "administrativo", "digital"],
            ),
            LegalReference(
                lei_numero="13.787/2018",
                orgao="Congresso Nacional",
                titulo="Documentos Eletronicos",
                dominio="digital",
                ementa="Dispoe sobre a validade juridica do documento eletronico.",
                artigos_relevantes=["1", "2", "3", "6", "8"],
                palavras_chave=["documento", "eletronico", "validade", "assintacao"],
            ),
        ]

        laws_tributarios = [
            LegalReference(
                lei_numero="5.172/1966",
                orgao="Congresso Nacional",
                titulo="Codigo Tributario Nacional",
                dominio="tributario",
                ementa="Dispoe sobre o sistema tributario nacional.",
                artigos_relevantes=["1", "3", "113", "116", "138"],
                palavras_chave=["tributo", "imposto", "taxa", "contribuicao", "fazenda"],
            ),
            LegalReference(
                lei_numero="12.715/2012",
                orgao="Congresso Nacional",
                titulo="Regime Especial de Tributacao para Plataformas Digitais",
                dominio="tributario",
                ementa="Dispoe sobre o regime especial de tributacao.",
                artigos_relevantes=["1", "2", "3"],
                palavras_chave=["plataforma", "digital", "tributacao", "simplificada"],
            ),
        ]

        laws_ambiental = [
            LegalReference(
                lei_numero="9.605/1998",
                orgao="Congresso Nacional",
                titulo="Lei de Crimes Ambientais",
                dominio="ambiental",
                ementa="Dispoe sobre as sancoes penais e administrativas derivadas de condutas lesivas ao meio ambiente.",
                artigos_relevantes=["1", "2", "3", "7", "8"],
                palavras_chave=["ambiental", "crime", "poluicao", "meio ambiente"],
            ),
        ]

        laws_propriedade_intelectual = [
            LegalReference(
                lei_numero="9.609/1998",
                orgao="Congresso Nacional",
                titulo="Lei de Protecao de Programas de Computador",
                dominio="propriedade_intelectual",
                ementa="Dispoe sobre a protecao da propriedade intelectual de programa de computador.",
                artigos_relevantes=["1", "2", "4", "5", "6"],
                palavras_chave=["software", "programa", "computador", "direito", "autor"],
            ),
            LegalReference(
                lei_numero="9.279/1996",
                orgao="Congresso Nacional",
                titulo="Lei de Patentes e Marcas",
                dominio="propriedade_intelectual",
                ementa="Dispoe sobre a protecao da propriedade industrial.",
                artigos_relevantes=["1", "2", "3", "8", "11", "13"],
                palavras_chave=["patente", "marca", "industrial", "invencao", "registro"],
            ),
        ]

        all_laws = (
            laws_dados_pessoais
            + laws_trabalhistas
            + laws_empresariais
            + laws_consumidor
            + laws_digital
            + laws_tributarios
            + laws_ambiental
            + laws_propriedade_intelectual
        )

        for law in all_laws:
            if law.dominio not in self._local_db:
                self._local_db[law.dominio] = []
            self._local_db[law.dominio].append(law)

    def _count_laws(self) -> int:
        return sum(len(laws) for laws in self._local_db.values())

    async def search(
        self,
        dominio: str,
        contexto: str = "",
    ) -> list[LegalReference]:
        laws = self._local_db.get(dominio, [])

        if not contexto:
            return laws

        scored = []
        contexto_lower = contexto.lower()
        for law in laws:
            score = 0
            for kw in law.palavras_chave:
                if kw in contexto_lower:
                    score += 2
            if dominio in contexto_lower:
                score += 1
            scored.append((score, law))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [law for _, law in scored]

    async def add_law(self, law: LegalReference):
        if law.dominio not in self._local_db:
            self._local_db[law.dominio] = []
        self._local_db[law.dominio].append(law)

        if self._redis:
            key = f"{self.LAWS_PREFIX}{law.lei_numero}"
            data = json.dumps({
                "lei_numero": law.lei_numero,
                "orgao": law.orgao,
                "titulo": law.titulo,
                "dominio": law.dominio,
                "ementa": law.ementa,
                "artigos_relevantes": law.artigos_relevantes,
                "palavras_chave": law.palavras_chave,
            }, ensure_ascii=False)
            await self._redis.set(key, data)
            await self._redis.sadd(self.DOMAINS_KEY, law.dominio)

    async def _persist_to_redis(self):
        if not self._redis:
            return
        pipe = self._redis.pipeline()
        for dominio, laws in self._local_db.items():
            for law in laws:
                key = f"{self.LAWS_PREFIX}{law.lei_numero}"
                data = json.dumps({
                    "lei_numero": law.lei_numero,
                    "orgao": law.orgao,
                    "titulo": law.titulo,
                    "dominio": law.dominio,
                    "ementa": law.ementa,
                    "artigos_relevantes": law.artigos_relevantes,
                    "palavras_chave": law.palavras_chave,
                }, ensure_ascii=False)
                pipe.set(key, data)
                pipe.sadd(self.DOMAINS_KEY, law.dominio)
        await pipe.execute()

    async def get_domain_stats(self) -> dict:
        stats = {}
        for dominio, laws in self._local_db.items():
            stats[dominio] = len(laws)
        return stats
