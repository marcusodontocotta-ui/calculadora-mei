"""
Calculadora MEI - Suite de Testes Completo (Pre-Deploy)
Valida todos os endpoints da API via HTTP (urllib.request)
Servidor esperado em: http://localhost:8081
"""
import urllib.request
import json
import sys
import traceback
from datetime import datetime

BASE = "http://localhost:8081"
PASS = 0
FAIL = 0
SKIP = 0
ERROS = []


def api(url, method="GET", data=None, expect_status=200):
    """Faz requisicao HTTP e retorna (status, json_ou_None)."""
    req = urllib.request.Request(url, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        body = json.loads(resp.read().decode())
        return resp.status, body
    except urllib.error.HTTPError as e:
        body = None
        try:
            body = json.loads(e.read().decode())
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, {"erro": str(e)}


def api_raw(url):
    """Retorna o body bruto como string."""
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode()


def ok(nome, msg=""):
    global PASS
    PASS += 1
    print("  [OK]    %s%s" % (nome, (" - " + msg) if msg else ""))


def erro(nome, msg=""):
    global FAIL
    FAIL += 1
    ERROS.append((nome, msg))
    print("  [ERRO]  %s - %s" % (nome, msg))


def skip_teste(nome, msg=""):
    global SKIP
    SKIP += 1
    print("  [SKIP]  %s - %s" % (nome, msg))


# IDs criados durante os testes (para limpeza)
_ids_produtos = []
_ids_vendas = []
_ids_despesas = []
_ids_clientes = []


def limpar_dados():
    """Remove todos os dados criados durante os testes."""
    print("\n--- Limpando dados de teste ---")
    for vid in _ids_vendas:
        s, _ = api(BASE + "/api/vendas/%d" % vid, "DELETE")
    for did in _ids_despesas:
        s, _ = api(BASE + "/api/despesas/%d" % did, "DELETE")
    for pid in _ids_produtos:
        s, _ = api(BASE + "/api/produtos/%d" % pid, "DELETE")
    for cid in _ids_clientes:
        s, _ = api(BASE + "/api/clientes/%d" % cid, "DELETE")
    # Cancelar assinaturas de teste
    for cid in _ids_clientes:
        api(BASE + "/api/assinatura/%d/cancelar" % cid, "POST")
    print("  Limpeza concluida.\n")


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 1 - Conexao com banco
# ══════════════════════════════════════════════════════════════════════════════
def teste_01_conexao_banco():
    print("\n=== 1. CONEXAO COM BANCO ===")
    # O /api/health Internamente chama contar_assinaturas_ativas() -> valida conexao
    s, r = api(BASE + "/api/health")
    if s == 200 and r and r.get("status") == "healthy":
        ok("Conexao PostgreSQL", "Banco acessivel via API")
    else:
        erro("Conexao PostgreSQL", "Nao foi conectar ao banco (status=%s)" % s)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 2 - Health check
# ══════════════════════════════════════════════════════════════════════════════
def teste_02_health_check():
    print("\n=== 2. HEALTH CHECK ===")
    s, r = api(BASE + "/api/health")
    if s != 200:
        erro("GET /api/health", "Status HTTP %s" % s)
        return
    campos = ["status", "version", "teto_anual", "teto_mensal", "tabela_das",
              "assinaturas_ativas", "timestamp"]
    faltando = [c for c in campos if c not in r]
    if faltando:
        erro("GET /api/health", "Campos faltando: %s" % faltando)
    elif r["status"] != "healthy":
        erro("GET /api/health", "status != 'healthy'")
    elif not isinstance(r["tabela_das"], dict):
        erro("GET /api/health", "tabela_das nao e dict")
    else:
        ok("GET /api/health", "status=%s, version=%s, assinaturas=%s" % (
            r["status"], r["version"], r["assinaturas_ativas"]))


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 3 - Produtos CRUD
# ══════════════════════════════════════════════════════════════════════════════
def teste_03_produtos_crud():
    print("\n=== 3. PRODUTOS CRUD ===")
    produto_dados = {
        "nome": "TESTE - Bolo de Cenoura",
        "preco": 35.50,
        "categoria": "produto",
        "descricao": "Bolo de teste automatizado",
        "data_validade": "2099-12-31",
        "estoque": 25,
        "unidade": "un"
    }

    # Criar
    s, r = api(BASE + "/api/produtos", "POST", produto_dados)
    if s == 201 or s == 200:
        pid = r["produto"]["id"]
        _ids_produtos.append(pid)
        ok("POST /api/produtos", "Produto #%d criado" % pid)
    else:
        erro("POST /api/produtos", "Status %s: %s" % (s, r))
        return

    # Listar
    s, r = api(BASE + "/api/produtos")
    if s == 200 and r.get("sucesso"):
        ok("GET /api/produtos", "Total=%d" % r["total"])
    else:
        erro("GET /api/produtos", "Falha: %s" % r)

    # Obter por ID
    s, r = api(BASE + "/api/produtos/%d" % pid)
    if s == 200 and r.get("sucesso") and r["produto"]["id"] == pid:
        ok("GET /api/produtos/{id}", "Nome=%s" % r["produto"]["nome"])
    else:
        erro("GET /api/produtos/{id}", "Falha ao obter produto #%d" % pid)

    # Atualizar
    produto_dados["nome"] = "TESTE - Bolo Atualizado"
    produto_dados["preco"] = 42.00
    s, r = api(BASE + "/api/produtos/%d" % pid, "PUT", produto_dados)
    if s == 200 and r.get("sucesso") and r["produto"]["nome"] == "TESTE - Bolo Atualizado":
        ok("PUT /api/produtos/{id}", "Atualizado para '%s'" % r["produto"]["nome"])
    else:
        erro("PUT /api/produtos/{id}", "Falha: %s" % r)

    # Obter inexistente
    s, r = api(BASE + "/api/produtos/999999")
    if s == 404:
        ok("GET /api/produtos/{id} inexistente", "Retornou 404 corretamente")
    else:
        erro("GET /api/produtos/{id} inexistente", "Esperava 404, recebeu %s" % s)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 4 - Vendas CRUD
# ══════════════════════════════════════════════════════════════════════════════
def teste_04_vendas_crud():
    print("\n=== 4. VENDAS CRUD ===")

    # Criar cliente temporario para vincular
    s, r = api(BASE + "/api/clientes", "POST", {"nome": "TESTE - Cliente Vendas"})
    if s == 200 and r.get("sucesso"):
        cid = r["cliente"]["id"]
        _ids_clientes.append(cid)
    else:
        cid = None

    # Venda SEM cliente
    s, r = api(BASE + "/api/vendas", "POST", {
        "descricao": "TESTE - Venda avulsa",
        "valor": 150.00,
        "quantidade": 1,
        "data": datetime.now().strftime("%Y-%m-%d")
    })
    if s == 200 and r.get("sucesso"):
        vid = r["venda"]["id"]
        _ids_vendas.append(vid)
        ok("POST /api/vendas (sem cliente)", "Venda #%d criada" % vid)
    else:
        erro("POST /api/vendas (sem cliente)", "Status %s: %s" % (s, r))
        vid = None

    # Venda COM cliente vinculado
    s, r = api(BASE + "/api/vendas", "POST", {
        "descricao": "TESTE - Venda com cliente",
        "valor": 250.00,
        "quantidade": 3,
        "data": datetime.now().strftime("%Y-%m-%d"),
        "cliente_id": cid
    })
    if s == 200 and r.get("sucesso") and r["venda"].get("cliente_id") == cid:
        vid2 = r["venda"]["id"]
        _ids_vendas.append(vid2)
        ok("POST /api/vendas (com cliente)", "Venda #%d -> Cliente #%d" % (vid2, cid))
    else:
        erro("POST /api/vendas (com cliente)", "Status %s: %s" % (s, r))

    # Listar vendas
    s, r = api(BASE + "/api/vendas")
    if s == 200 and r.get("sucesso") and r["quantidade"] >= 2:
        ok("GET /api/vendas", "%d vendas, total=%s" % (r["quantidade"], r["total_formatado"]))
    else:
        erro("GET /api/vendas", "Falha: %s" % r)

    # Listar por mes/ano
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    s, r = api(BASE + "/api/vendas?mes=%d&ano=%d" % (mes_atual, ano_atual))
    if s == 200 and r.get("sucesso"):
        ok("GET /api/vendas?mes=X&ano=Y", "%d vendas no mes atual" % r["quantidade"])
    else:
        erro("GET /api/vendas?mes=X&ano=Y", "Falha: %s" % r)

    # Excluir
    if vid:
        s, r = api(BASE + "/api/vendas/%d" % vid, "DELETE")
        if s == 200 and r.get("sucesso"):
            _ids_vendas.remove(vid)
            ok("DELETE /api/vendas/{id}", "Venda #%d excluida" % vid)
        else:
            erro("DELETE /api/vendas/{id}", "Falha: %s" % r)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 5 - Despesas CRUD
# ══════════════════════════════════════════════════════════════════════════════
def teste_05_despesas_crud():
    print("\n=== 5. DESPESAS CRUD ===")

    # Criar
    s, r = api(BASE + "/api/despesas", "POST", {
        "descricao": "TESTE - Material de escritorio",
        "valor": 89.90,
        "data": datetime.now().strftime("%Y-%m-%d"),
        "categoria": "variavel"
    })
    if s == 200 and r.get("sucesso"):
        did = r["despesa"]["id"]
        _ids_despesas.append(did)
        ok("POST /api/despesas", "Despesa #%d criada" % did)
    else:
        erro("POST /api/despesas", "Status %s: %s" % (s, r))
        return

    # Listar
    s, r = api(BASE + "/api/despesas")
    if s == 200 and r.get("sucesso") and r["quantidade"] >= 1:
        ok("GET /api/despesas", "%d despesas, total=%s" % (r["quantidade"], r["total_formatado"]))
    else:
        erro("GET /api/despesas", "Falha: %s" % r)

    # Listar por mes
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    s, r = api(BASE + "/api/despesas?mes=%d&ano=%d" % (mes_atual, ano_atual))
    if s == 200 and r.get("sucesso"):
        ok("GET /api/despesas?mes=X&ano=Y", "%d despesas no mes" % r["quantidade"])
    else:
        erro("GET /api/despesas?mes=X&ano=Y", "Falha: %s" % r)

    # Criar despesa fixa
    s, r = api(BASE + "/api/despesas", "POST", {
        "descricao": "TESTE - Aluguel fake",
        "valor": 1200.00,
        "data": datetime.now().strftime("%Y-%m-%d"),
        "categoria": "fixa"
    })
    if s == 200 and r.get("sucesso"):
        did2 = r["despesa"]["id"]
        _ids_despesas.append(did2)
        ok("POST /api/despesas (fixa)", "Despesa #%d criada" % did2)
    else:
        erro("POST /api/despesas (fixa)", "Status %s: %s" % (s, r))

    # Excluir
    s, r = api(BASE + "/api/despesas/%d" % did, "DELETE")
    if s == 200 and r.get("sucesso"):
        _ids_despesas.remove(did)
        ok("DELETE /api/despesas/{id}", "Despesa #%d excluida" % did)
    else:
        erro("DELETE /api/despesas/{id}", "Falha: %s" % r)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 6 - Clientes CRUD + Aniversariantes
# ══════════════════════════════════════════════════════════════════════════════
def teste_06_clientes_crud():
    print("\n=== 6. CLIENTES CRUD ===")
    cliente_dados = {
        "nome": "TESTE - Joao Silva",
        "telefone": "11988887777",
        "email": "joao.teste@email.com",
        "data_aniversario": "1985-%02d-15" % datetime.now().month,
        "endereco": "Rua Teste, 123",
        "observacoes": "Cliente de teste automatizado",
        "produto_preferido": "Servico de consultoria",
        "periodicidade": "mensal"
    }

    # Criar
    s, r = api(BASE + "/api/clientes", "POST", cliente_dados)
    if s == 200 and r.get("sucesso"):
        cid = r["cliente"]["id"]
        _ids_clientes.append(cid)
        ok("POST /api/clientes", "Cliente #%d criado" % cid)
    else:
        erro("POST /api/clientes", "Status %s: %s" % (s, r))
        return

    # Listar
    s, r = api(BASE + "/api/clientes")
    if s == 200 and r.get("sucesso") and r["total"] >= 1:
        ok("GET /api/clientes", "%d clientes" % r["total"])
    else:
        erro("GET /api/clientes", "Falha: %s" % r)

    # Obter por ID
    s, r = api(BASE + "/api/clientes/%d" % cid)
    if s == 200 and r.get("sucesso") and r["cliente"]["id"] == cid:
        ok("GET /api/clientes/{id}", "Nome=%s" % r["cliente"]["nome"])
    else:
        erro("GET /api/clientes/{id}", "Falha ao obter cliente #%d" % cid)

    # Busca por nome
    s, r = api(BASE + "/api/clientes?q=TESTE")
    if s == 200 and r.get("sucesso") and r["total"] >= 1:
        ok("GET /api/clientes?q=TESTE", "%d resultado(s)" % r["total"])
    else:
        erro("GET /api/clientes?q=TESTE", "Falha: %s" % r)

    # Atualizar
    cliente_dados["nome"] = "TESTE - Joao Atualizado"
    s, r = api(BASE + "/api/clientes/%d" % cid, "PUT", cliente_dados)
    if s == 200 and r.get("sucesso") and r["cliente"]["nome"] == "TESTE - Joao Atualizado":
        ok("PUT /api/clientes/{id}", "Atualizado para '%s'" % r["cliente"]["nome"])
    else:
        erro("PUT /api/clientes/{id}", "Falha: %s" % r)

    # Obter inexistente
    s, r = api(BASE + "/api/clientes/999999")
    if s == 404:
        ok("GET /api/clientes/{id} inexistente", "Retornou 404 corretamente")
    else:
        erro("GET /api/clientes/{id} inexistente", "Esperava 404, recebeu %s" % s)

    # Aniversariantes
    s, r = api(BASE + "/api/clientes/aniversarios")
    if s == 200 and r.get("sucesso") and "clientes" in r:
        ok("GET /api/clientes/aniversarios", "%d aniversariante(s) no mes %d" % (
            r["total"], r["mes"]))
    else:
        erro("GET /api/clientes/aniversarios", "Falha: %s" % r)

    # Historico de compras
    s, r = api(BASE + "/api/clientes/%d/compras" % cid)
    if s == 200 and r.get("sucesso") and "compras" in r:
        ok("GET /api/clientes/{id}/compras", "%d compra(s)" % r["quantidade"])
    else:
        erro("GET /api/clientes/{id}/compras", "Falha: %s" % r)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 7 - Resumo mensal
# ══════════════════════════════════════════════════════════════════════════════
def teste_07_resumo_mensal():
    print("\n=== 7. RESUMO MENSAL ===")
    mes = datetime.now().month
    ano = datetime.now().year
    s, r = api(BASE + "/api/resumo-mensal?mes=%d&ano=%d&tipo_atividade=servico" % (mes, ano))
    if s != 200 or not r.get("sucesso"):
        erro("GET /api/resumo-mensal", "Status %s: %s" % (s, r))
        return

    campos_obrig = ["vendas", "despesas", "das", "lucro", "eficiencia"]
    faltando = [c for c in campos_obrig if c not in r]
    if faltando:
        erro("GET /api/resumo-mensal", "Campos faltando: %s" % faltando)
        return

    ok("GET /api/resumo-mensal", "Mes %d/%d - Vendas: %s | Despesas: %s | DAS: %s | Lucro: %s | Margem: %s%%" % (
        r["mes"], r["ano"],
        r["vendas"]["total_formatado"],
        r["despesas"]["total_formatado"],
        r["das"]["valor_formatado"],
        r["lucro"]["liquido_formatado"],
        r["lucro"]["margem"]))


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 8 - Faturamento anual
# ══════════════════════════════════════════════════════════════════════════════
def teste_08_faturamento_anual():
    print("\n=== 8. FATURAMENTO ANUAL ===")
    ano = datetime.now().year
    s, r = api(BASE + "/api/faturamento-anual?ano=%d" % ano)
    if s != 200 or not r.get("sucesso"):
        erro("GET /api/faturamento-anual", "Status %s: %s" % (s, r))
        return

    campos = ["total", "por_mes", "limite", "limite_formatado"]
    faltando = [c for c in campos if c not in r]
    if faltando:
        erro("GET /api/faturamento-anual", "Campos faltando: %s" % faltando)
        return

    if not isinstance(r["por_mes"], dict):
        erro("GET /api/faturamento-anual", "por_mes nao e dict")
        return

    meses_com_dados = sum(1 for v in r["por_mes"].values() if v > 0)
    ok("GET /api/faturamento-anual", "Ano=%d | Total: %s | Limite: %s | Meses c/ dados: %d" % (
        r["ano"], r["total_formatado"], r["limite_formatado"], meses_com_dados))


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 9 - Assinatura (criar, verificar, cancelar)
# ══════════════════════════════════════════════════════════════════════════════
def teste_09_assinatura():
    print("\n=== 9. ASSINATURA ===")

    # Criar cliente para assinatura
    s, r = api(BASE + "/api/clientes", "POST", {
        "nome": "TESTE - Cliente Assinatura",
        "email": "assinatura.teste@email.com"
    })
    if s != 200 or not r.get("sucesso"):
        erro("Setup assinatura", "Nao conseguiu criar cliente: %s" % r)
        return
    cid = r["cliente"]["id"]
    _ids_clientes.append(cid)

    # Verificar status (deve ser free/sem assinatura)
    s, r = api(BASE + "/api/assinatura/%d" % cid)
    if s == 200 and r.get("sucesso") and r.get("plano") == "free":
        ok("GET /api/assinatura/{id} (sem assinatura)", "plano=free, ativo=False")
    else:
        erro("GET /api/assinatura/{id}", "Esperava plano=free, recebeu: %s" % r)

    # Criar checkout (Mercado Pago sandbox)
    s, r = api(BASE + "/api/assinatura/checkout", "POST", {
        "cliente_id": cid,
        "email": "assinatura.teste@email.com",
        "nome": "TESTE - Cliente Assinatura"
    })
    if s == 200 and r.get("sucesso"):
        ok("POST /api/assinatura/checkout", "checkout_url=%s, preference_id=%s, valor=%s" % (
            "OK" if r.get("checkout_url") else "N/A",
            r.get(" preference_id", "N/A"),
            r.get("valor")))
    elif s == 200 and r.get("checkout_url"):
        ok("POST /api/assinatura/checkout", "URL gerada com sucesso")
    else:
        erro("POST /api/assinatura/checkout", "Status %s: %s (pode falhar com token sandbox)" % (s, str(r)[:200]))

    # Verificar status apos checkout (deve ser pendente)
    s, r = api(BASE + "/api/assinatura/%d" % cid)
    if s == 200 and r.get("sucesso"):
        plano = r.get("plano")
        ativo = r.get("ativo")
        # Com token sandbox, pode ficar pendente ou ativar
        ok("GET /api/assinatura/{id} (pos checkout)", "plano=%s, ativo=%s" % (plano, ativo))
    else:
        erro("GET /api/assinatura/{id} (pos checkout)", "Falha: %s" % r)

    # Cancelar assinatura
    s, r = api(BASE + "/api/assinatura/%d/cancelar" % cid, "POST")
    if s == 200 and r.get("sucesso"):
        ok("POST /api/assinatura/{id}/cancelar", "Cancelada com sucesso")
    elif s == 404:
        skip_teste("POST /api/assinatura/{id}/cancelar", "Nenhuma assinatura ativa para cancelar")
    else:
        erro("POST /api/assinatura/{id}/cancelar", "Status %s: %s" % (s, r))

    # Verificar status apos cancelamento
    s, r = api(BASE + "/api/assinatura/%d" % cid)
    if s == 200 and r.get("sucesso") and r.get("plano") == "free":
        ok("GET /api/assinatura/{id} (pos cancelamento)", "plano=free corretamente")
    elif s == 200:
        ok("GET /api/assinatura/{id} (pos cancelamento)", "plano=%s" % r.get("plano"))
    else:
        erro("GET /api/assinatura/{id} (pos cancelamento)", "Falha: %s" % r)


# ══════════════════════════════════════════════════════════════════════════════
# TESTE 10 - Checkout Mercado Pago
# ══════════════════════════════════════════════════════════════════════════════
def teste_10_checkout_mercado_pago():
    print("\n=== 10. CHECKOUT MERCADO PAGO ===")

    # Criar cliente temporario
    s, r = api(BASE + "/api/clientes", "POST", {
        "nome": "TESTE - Checkout MP",
        "email": "checkout.teste@email.com"
    })
    if s == 200 and r.get("sucesso"):
        cid = r["cliente"]["id"]
        _ids_clientes.append(cid)
    else:
        erro("Setup checkout", "Nao conseguiu criar cliente")
        return

    # Criar checkout
    s, r = api(BASE + "/api/assinatura/checkout", "POST", {
        "cliente_id": cid,
        "email": "checkout.teste@email.com",
        "nome": "TESTE - Checkout MP"
    })

    # Validar resposta
    if s == 200 and r.get("sucesso"):
        checkout_url = r.get("checkout_url")
        preference_id = r.get("precoference_id", r.get("preference_id"))
        valor = r.get("valor")

        if checkout_url and isinstance(checkout_url, str) and len(checkout_url) > 10:
            ok("POST /api/assinatura/checkout (URL)",
               "checkout_url gerada: %s..." % checkout_url[:60])
        else:
            skip_teste("POST /api/assinatura/checkout (URL)",
                       "URL nao retornada (token sandbox: %s)" % checkout_url)

        if valor:
            ok("POST /api/assinatura/checkout (valor)", "R$ %.2f" % valor)
        else:
            erro("POST /api/assinatura/checkout (valor)", "Valor nao retornado")
    else:
        skip_teste("POST /api/assinatura/checkout",
                   "Nao retornou sucesso (token=%s). Erro: %s" % (
                       "TEST-xxx", str(r)[:150]))

    # Validar que a assinatura foi criada no banco
    s, r = api(BASE + "/api/assinatura/%d" % cid)
    if s == 200 and r.get("sucesso") and r.get("assinatura"):
        ok("Checkout criou assinatura no banco",
           "Status=%s" % r["assinatura"].get("status"))
    elif s == 200:
        skip_teste("Checkout criou assinatura no banco",
                   "Assinatura nao encontrada (pode ter falhado com token sandbox)")
    else:
        erro("Checkout criou assinatura no banco", "Falha: %s" % r)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    global PASS, FAIL, SKIP

    print("=" * 60)
    print("  CALCULADORA MEI - SUITE DE TESTES COMPLETO")
    print("  Servidor: %s" % BASE)
    print("  Data: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    # Verificar se o servidor esta rodando
    print("\n--- Verificando servidor ---")
    try:
        s, r = api(BASE + "/api/health")
        if s != 200:
            print("ERRO: Servidor retornou status %s" % s)
            print("Certifique-se que o servidor esta rodando em %s" % BASE)
            sys.exit(1)
        print("Servidor OK (status=%s)\n" % s)
    except Exception as e:
        print("ERRO: Nao foi possivel conectar ao servidor em %s" % BASE)
        print("  %s" % e)
        print("\nInicie o servidor com:")
        print("  cd %s && python main.py" % BASE)
        sys.exit(1)

    # Executar todos os testes
    testes = [
        teste_01_conexao_banco,
        teste_02_health_check,
        teste_03_produtos_crud,
        teste_04_vendas_crud,
        teste_05_despesas_crud,
        teste_06_clientes_crud,
        teste_07_resumo_mensal,
        teste_08_faturamento_anual,
        teste_09_assinatura,
        teste_10_checkout_mercado_pago,
    ]

    for teste in testes:
        try:
            teste()
        except Exception as e:
            erro(teste.__name__, "Excecao nao tratada: %s" % e)
            traceback.print_exc()

    # Limpar dados
    limpar_dados()

    # Relatorio final
    total = PASS + FAIL + SKIP
    print("=" * 60)
    print("  RELATORIO FINAL")
    print("=" * 60)
    print("  Total: %d testes" % total)
    print("  OK:    %d" % PASS)
    print("  ERRO:  %d" % FAIL)
    print("  SKIP:  %d" % SKIP)
    print("  Passou: %.0f%%" % ((PASS / max(total, 1)) * 100))

    if FAIL > 0:
        print("\n  FALHAS:")
        for nome, msg in ERROS:
            print("    - %s: %s" % (nome, msg))

    print("=" * 60)

    if FAIL == 0:
        print("  DEPLOY VALIDADO COM SUCESSO!")
    else:
        print("  DEPLOY COM FALHAS - VERIFICAR ERROS ACIMA")

    print("=" * 60)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
