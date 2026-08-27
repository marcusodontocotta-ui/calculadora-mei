import urllib.request
import json

def api(url, method='GET', data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode()
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Listar rotas
resp = urllib.request.urlopen('http://localhost:8081/openapi.json')
api_data = json.loads(resp.read())
paths = list(api_data.get('paths', {}).keys())
print("ROTAS: %d" % len(paths))
for p in paths:
    print("  %s" % p)
print()

# Dashboard
print("=== DASHBOARD ===")
r = api('http://localhost:8081/api/dashboard')
print("OK")
print()

# Cadastrar cliente
print("=== CADASTRAR CLIENTE ===")
r = api('http://localhost:8081/api/clientes', 'POST', {
    'nome': 'Maria Silva',
    'telefone': '11999998888',
    'email': 'maria@email.com',
    'data_aniversario': '1990-07-15',
    'produto_preferido': 'Bolo de Chocolate',
    'periodicidade': 'semanal'
})
c = r['cliente']
print("Cliente #%d: %s - Tel: %s - Aniv: %s" % (c['id'], c['nome'], c.get('telefone',''), c.get('data_aniversario','')))
print()

# Cadastrar produto
print("=== CADASTRAR PRODUTO ===")
r = api('http://localhost:8081/api/produtos', 'POST', {
    'nome': 'Bolo de Chocolate',
    'preco': 45.00,
    'categoria': 'produto',
    'data_validade': '2025-08-25',
    'estoque': 10,
    'unidade': 'un'
})
p = r['produto']
print("Produto #%d: %s - %s" % (p['id'], p['nome'], p['preco_formatado']))
if p.get('status_validade'):
    print("  Validade: %s" % p['status_validade']['mensagem'])
print()

# Registrar venda com cliente
print("=== REGISTRAR VENDA COM CLIENTE ===")
r = api('http://localhost:8081/api/vendas', 'POST', {
    'descricao': 'Bolo de Chocolate',
    'valor': 90.00,
    'quantidade': 2,
    'data': '2025-08-20',
    'cliente_id': 1,
    'produto_id': 1
})
v = r['venda']
print("Venda #%d: %s -> Cliente #%s" % (v['id'], v['valor_formatado'], v.get('cliente_id', 'N/A')))
print()

# Despesas
print("=== REGISTRAR DESPESAS ===")
r = api('http://localhost:8081/api/despesas', 'POST', {
    'descricao': 'Farinha',
    'valor': 35.00,
    'data': '2025-08-18',
    'categoria': 'material'
})
d = r['despesa']
print("Despesa #%d: %s - material - R$ %.2f" % (d['id'], d['descricao'], d['valor']))

r = api('http://localhost:8081/api/despesas', 'POST', {
    'descricao': 'Aluguel',
    'valor': 800.00,
    'data': '2025-08-05',
    'categoria': 'fixa'
})
d = r['despesa']
print("Despesa #%d: %s - fixa - R$ %.2f" % (d['id'], d['descricao'], d['valor']))
print()

# Resumo mensal
print("=== RESUMO MENSAL (AGO/2025) ===")
r = api('http://localhost:8081/api/resumo-mensal?mes=8&ano=2025')
print("Vendas: %s (%d)" % (r['vendas']['total_formatado'], r['vendas']['quantidade']))
print("Despesas: %s" % r['despesas']['total_formatado'])
print("DAS: %s" % r['das']['valor_formatado'])
print("Lucro Liquido: %s" % r['lucro']['liquido_formatado'])
print("Margem: %s%%" % r['lucro']['margem'])
print("Eficiencia: %s%% - %s" % (r['eficiencia']['percentual'], r['eficiencia']['mensagem']))
print()

# Aniversariantes
print("=== ANIVERSARIANTES DO MES ===")
r = api('http://localhost:8081/api/clientes/aniversarios')
print("Aniversariantes: %d" % len(r['clientes']))
for c in r['clientes']:
    print("  - %s (aniv: %s)" % (c['nome'], c.get('data_aniversario', '')))
print()

# Historico de compras
print("=== HISTORICO DE COMPRAS ===")
r = api('http://localhost:8081/api/clientes/1/compras')
print("Compras de %s: %d vendas" % (r['cliente']['nome'], len(r['compras'])))
for v in r['compras']:
    print("  - %s: %s" % (v['descricao'], v['valor_formatado']))
print()

# Faturamento anual
print("=== FATURAMENTO ANUAL ===")
r = api('http://localhost:8081/api/faturamento-anual?ano=2025')
print("Total: %s / Limite: %s" % (r['total_formatado'], r['limite_formatado']))
for m, v in r['por_mes'].items():
    if v > 0:
        print("  Mes %s: R$ %.2f" % (m, v))
print()

print("=" * 50)
print("TODOS OS TESTES OK!")
print("=" * 50)
