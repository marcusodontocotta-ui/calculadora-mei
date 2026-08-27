"""
Calculadora MEI - Modulo de Calculos
Baseado na legislacao vigente (Lei 12.846/2013 e atualizacoes 2024/2025)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import calendar


@dataclass
class ResultadoDAS:
    """Resultado do calculo do DAS mensal."""
    mes: int
    ano: int
    faturamento: float
    teto_anual: float
    dentro_do_teto: bool
    aliquota: float
    inss: float
    icms: float
    iss: float
    valor_total: float
    data_vencimento: str
    dias_ate_vencer: int
    pode_emitir_nfe: bool


@dataclass
class CenarioSimulacao:
    """Simulacao de cenarios de faturamento."""
    nome: str
    faturamento_mensal: float
    custos_fixos: float
    custos_variaveis_pct: float
    meses: int


@dataclass
class ResultadoSimulacao:
    """Resultado da simulacao."""
    cenario: CenarioSimulacao
    faturamento_anual: float
    lucro_bruto: float
    lucro_liquido: float
    das_anual: float
    margem_eff: float
    roi_meses: float


# Tabela DAS MEI 2025 (valores atualizados conforme Lei 14.848/2024)
TABELA_DAS_2025 = {
    "comercio": {
        "inss": 75.00,
        "icms": 75.00,
    },
    "servico": {
        "inss": 75.00,
        "iss": 75.00,
    },
    "misto": {
        "inss": 75.00,
        "icms": 75.00,
        "iss": 75.00,
    }
}

# Teto de faturamento MEI 2025
TETO_ANUAL_2025 = 81_000.00
TETO_MENSAL_2025 = TETO_ANUAL_2025 / 12

# Vencimento do DAS: dia 20 de cada mes
DIA_VENCIMENTO = 20


def calcular_das(
    mes: int,
    ano: int,
    faturamento: float,
    tipo_atividade: str = "servico"
) -> ResultadoDAS:
    """
    Calcula o valor do DAS mensal do MEI.
    """
    if tipo_atividade not in TABELA_DAS_2025:
        tipo_atividade = "servico"

    tabela = TABELA_DAS_2025[tipo_atividade]
    inss = tabela["inss"]

    if tipo_atividade == "comercio":
        icms = tabela["icms"]
        iss = 0.0
    elif tipo_atividade == "servico":
        icms = 0.0
        iss = tabela["iss"]
    else:
        icms = tabela.get("icms", 75.00)
        iss = tabela.get("iss", 75.00)

    valor_total = inss + icms + iss

    faturamento_anual_projecao = faturamento * 12
    dentro_do_teto = faturamento_anual_projecao <= TETO_ANUAL_2025

    try:
        data_venc = datetime(ano, mes, DIA_VENCIMENTO)
    except ValueError:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_venc = datetime(ano, min(DIA_VENCIMENTO, ultimo_dia), 1)

    hoje = datetime.now()
    dias_ate_vencer = (data_venc - hoje).days

    pode_nfe = dentro_do_teto and faturamento <= TETO_MENSAL_2025

    return ResultadoDAS(
        mes=mes,
        ano=ano,
        faturamento=faturamento,
        teto_anual=TETO_ANUAL_2025,
        dentro_do_teto=dentro_do_teto,
        aliquota=0.0,
        inss=inss,
        icms=icms,
        iss=iss,
        valor_total=valor_total,
        data_vencimento=data_venc.strftime("%d/%m/%Y"),
        dias_ate_vencer=dias_ate_vencer,
        pode_emitir_nfe=pode_nfe
    )


def simular_cenarios(cenarios: list) -> list:
    """Simula multiplos cenarios de faturamento."""
    resultados = []

    for cenario in cenarios:
        faturamento_anual = cenario.faturamento_mensal * 12
        custos_fixos_anual = cenario.custos_fixos * 12
        custos_variaveis = faturamento_anual * (cenario.custos_variaveis_pct / 100)

        meses_no_teto = min(12, int(TETO_ANUAL_2025 / cenario.faturamento_mensal)) if cenario.faturamento_mensal > 0 else 0
        das_anual = meses_no_teto * TABELA_DAS_2025["servico"]["inss"] + \
                   meses_no_teto * TABELA_DAS_2025["servico"]["iss"]

        lucro_bruto = faturamento_anual - custos_fixos_anual - custos_variaveis
        lucro_liquido = lucro_bruto - das_anual
        margem = (lucro_liquido / faturamento_anual * 100) if faturamento_anual > 0 else 0

        investimento_inicial = 2_000.00
        roi_meses = investimento_inicial / (lucro_liquido / 12) if lucro_liquido > 0 else float('inf')

        resultados.append(ResultadoSimulacao(
            cenario=cenario,
            faturamento_anual=faturamento_anual,
            lucro_bruto=lucro_bruto,
            lucro_liquido=lucro_liquido,
            das_anual=das_anual,
            margem_eff=margem,
            roi_meses=roi_meses
        ))

    return resultados


def obter_alertas_vencimento(mes: int, ano: int) -> dict:
    """Retorna alertas de vencimento do DAS."""
    try:
        data_venc = datetime(ano, mes, DIA_VENCIMENTO)
    except ValueError:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_venc = datetime(ano, mes, ultimo_dia)

    hoje = datetime.now()
    dias_restantes = (data_venc - hoje).days

    if dias_restantes < 0:
        nivel = "vencido"
        mensagem = f"DAS vencido ha {abs(dias_restantes)} dias! Multa de 2% ao dia."
    elif dias_restantes <= 3:
        nivel = "critico"
        mensagem = f"FALTAM {dias_restantes} DIAS para vencimento!"
    elif dias_restantes <= 7:
        nivel = "alerta"
        mensagem = f"Faltam {dias_restantes} dias para vencimento."
    elif dias_restantes <= 14:
        nivel = "info"
        mensagem = f"Vencimento em {dias_restantes} dias."
    else:
        nivel = "ok"
        mensagem = f"Vencimento em {dias_restantes} dias."

    return {
        "nivel": nivel,
        "mensagem": mensagem,
        "dias_restantes": dias_restantes,
        "data_vencimento": data_venc.strftime("%d/%m/%Y"),
        "valor_multa_se_atrasar": round(TABELA_DAS_2025["servico"]["inss"] * 0.02 * abs(dias_restantes) if dias_restantes < 0 else 0, 2)
    }


def formatar_moeda(valor: float) -> str:
    """Formata valor em Reais."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_meses_restantes_ano(ano: int) -> int:
    """Retorna quantos meses restam no ano."""
    mes_atual = datetime.now().month if datetime.now().year == ano else 1
    return 12 - mes_atual + 1
