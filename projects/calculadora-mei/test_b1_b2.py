"""
Testes unitarios (B1 e B2) da Calculadora MEI.

B1: conferencia do valor do pagamento aprovado contra o valor_esperado da
    assinatura/cupom, antes de ativar/renovar o PRO (com tolerancia de centavos).
B2: logica de token de confirmacao de posse de email (hash + endpoint/marca).

Nao exige conexao com banco nem rede (apenas importa as funcoes puras).
Define DATABASE_URL dummy para permitir o import (a pool e criada sob demanda).
"""
import asyncio
import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

import database  # noqa: E402
import main  # noqa: E402


def test_b1_valor_efetivo_pagamento():
    assert main._valor_efetivo_pagamento({"transaction_amount": 9.90}) == 9.90
    assert main._valor_efetivo_pagamento({"transaction_amount": 9.90, "transaction_amount_refunded": 9.90}) == 0.0
    assert main._valor_efetivo_pagamento({"transaction_amount": 6.93, "transaction_amount_refunded": 0.0}) == 6.93


def test_b1_valor_confere_tolerancia():
    # valor exato
    assert main._valor_confere(9.90, 9.90) is True
    # diferenca de 1 centavo (aceita - evita falso-negativo)
    assert main._valor_confere(9.90, 9.91) is True
    assert main._valor_confere(9.90, 9.89) is True
    # fracao com cupom
    assert main._valor_confere(6.93, 6.93) is True
    # valor claramente divergente
    assert main._valor_confere(9.90, 5.00) is False
    assert main._valor_confere(9.90, 19.90) is False
    # arredondamento de centavos
    assert main._valor_confere(9.90, 9.895) is True


def run(async_fn, *args):
    return asyncio.run(async_fn(*args))


def test_b1_validar_valor_pagamento_certo():
    assinatura = {"id": 1, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 9.90}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay1") is True


def test_b1_validar_valor_pagamento_certo_abaixo_tolerancia():
    assinatura = {"id": 1, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 9.89}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay1") is True


def test_b1_validar_valor_pagamento_abaixo():
    assinatura = {"id": 1, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 5.00}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay1") is False


def test_b1_validar_valor_pagamento_acima():
    assinatura = {"id": 1, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 19.90}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay1") is False


def test_b1_validar_valor_pagamento_fracao_cupom():
    assinatura = {"id": 2, "valor_esperado": 6.93}
    pagamento = {"transaction_amount": 6.93}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay2") is True
    pagamento_errado = {"transaction_amount": 7.00}
    assert run(main._validar_valor_pagamento, assinatura, pagamento_errado, "pay3") is False


def test_b1_validar_valor_pagamento_refund_total():
    assinatura = {"id": 3, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 9.90, "transaction_amount_refunded": 9.90}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay4") is False


def test_b1_validar_valor_pagamento_refund_parcial():
    assinatura = {"id": 4, "valor_esperado": 9.90}
    pagamento = {"transaction_amount": 9.90, "transaction_amount_refunded": 4.95}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay5") is False


def test_b1_validar_valor_pagamento_legado_sem_esperado():
    assinatura = {"id": 5, "valor_esperado": None}
    pagamento = {"transaction_amount": 9.90}
    assert run(main._validar_valor_pagamento, assinatura, pagamento, "pay6") is True


def test_b2_hash_token_deterministico():
    t = "token-de-confirmacao-exemplo"
    assert database.hash_token(t) == database.hash_token(t)
    assert len(database.hash_token(t)) == 64
    assert database.hash_token(t) != t


def test_b2_token_roundtrip_mapeia_mesmo_hash():
    # Simula: cadastro grava hash; confirmacao procura pelo hash do token bruto.
    token_bruto = "tokencru_confirmacao_12345"
    armazenado = database.hash_token(token_bruto)
    chegada = database.hash_token(token_bruto)
    assert armazenado == chegada
    assert database.hash_token("outro-token") != armazenado  # token diferente nao confere


def test_b2_token_nao_gravado_em_texto_puro():
    # O hash nunca deve ser igual ao token bruto (nao grava valor em claro).
    token_bruto = main._novo_token()
    assert token_bruto != database.hash_token(token_bruto)
    assert database.hash_token(token_bruto) != token_bruto


if __name__ == "__main__":
    funcoes = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in funcoes:
        fn()
        print("OK", fn.__name__)
    print("TODOS OS TESTES PASSARAM:", len(funcoes))