# Code Review — Calculadora MEI

**Data da auditoria:** 2026-08-27
**Arquivos auditados:** `calculadora.py`, `main.py`, `database.py`, `static/app.js`
**Escopo:** bugs lógicos, performance, código morto, tratamento de erros, race conditions, validação de inputs e conformidade da tabela DAS 2025.

---

## Resumo executivo (prioridade de correção)

| Severidade | Quantidade |
|-----------|-----------|
| **ALTO** | 8 |
| **MÉDIO** | 9 |
| **BAIXO** | 5 |

O achado mais grave é a **tabela DAS 2025 com valores incorretos** (ACHADO A1), que faz o app cobrar/indicar um DAS **até ~2x o valor devido** em todos os tipos de atividade. Há também credenciais de produção hardcoded no código-fonte (A2) e graves problemas de performance em `/api/resumo-anual` e `/api/faturamento-anual` (A5/A6). A correção da A1 é obrigatória e urgente por ser app em produção compartilhando banco com o SISGERSA.

---

## ALTO — correção imediata

### A1. Tabela DAS 2025 com valores incorretos (superfaturamento)

**Arquivo:** `calculadora.py:51-66`

O código define:

```python
TABELA_DAS_2025 = {
    "comercio": {"inss": 75.00, "icms": 75.00},
    "servico":  {"inss": 75.00, "iss": 75.00},
    "misto":    {"inss": 75.00, "icms": 75.00, "iss": 75.00},
}
```

Os **valores oficiais 2025** (fonte gov.br / Receita, salário-mínimo R$ 1.518,00) são:

| Atividade | INSS (5% SM) | ICMS | ISS | Total correto | Total do código | % de erro |
|-----------|-------------|------|-----|---------------|-----------------|-----------|
| Comércio  | R$ 75,90    | R$ 1,00 | –   | **R$ 76,90** | R$ 150,00       | **+95%** |
| Serviço   | R$ 75,90    | –     | R$ 5,00 | **R$ 80,90** | R$ 150,00    | **+85%** |
| Misto     | R$ 75,90    | R$ 1,00 | R$ 5,00 | **R$ 81,90** | R$ 225,00    | **+175%** |

Além disso, a nota do código ("Lei 12.846/2013" / "Lei 14.848/2024") está equivocada — a base legal do MEI é a **LC 123/2006** (Estatuto das ME e EPP).

**Correção sugerida:**

```python
# Valores oficiais DAS MEI 2025 — INSS = 5% do salário-mínimo (R$ 1.518,00)
INSS_MEI_2025 = 75.90
ICMS_MEI_2025 = 1.00   # comércio/indústria
ISS_MEI_2025  = 5.00   # serviços

TABELA_DAS_2025 = {
    "comercio": {"inss": INSS_MEI_2025, "icms": ICMS_MEI_2025},
    "servico":  {"inss": INSS_MEI_2025, "iss": ISS_MEI_2025},
    "misto":    {"inss": INSS_MEI_2025, "icms": ICMS_MEI_2025, "iss": ISS_MEI_2025},
}
```

**IMPORTANTE:** duplicar/apagar o valor embutido em `static/app.js:273` (`const das = 150;` no `calcularEficiencia`), que também está superfaturado e hardcoded.

---

### A2. Credenciais de banco de produção hardcoded no código-fonte

**Arquivo:** `database.py:11-14`

```python
RAW_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sisgersa_app:ixnU2aktneWNQhJoqiiKRQs033NSUnM5@dpg-..."
)
```

A senha real do PostgreSQL de produção está commitada no repositório como *fallback*. Qualquer pessoa com acesso ao repo conecta no banco compartilhado com o SISGERSA.

**Correção sugerida:** remover o fallback e falhar rápido se a env não existir:

```python
RAW_DATABASE_URL = os.environ.get("DATABASE_URL")
if not RAW_DATABASE_URL:
    raise RuntimeError("DATABASE_URL nao definida. Configure a variavel de ambiente.")
```

Além disso, **rotacionar imediatamente** a senha exposta.

---

### A3. TLS com verificação de certificado desativada

**Arquivo:** `database.py:39-43`

```python
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
kwargs["ssl"] = ctx
```

Desativar a verificação do certificado abre o canal para ataque **man-in-the-middle** (credenciais e dados trafegando para um servidor falso). Postgres moderno já suporta SSL/TLS nativo via asyncpg.

**Correção sugerida:**

```python
pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
# asyncpg usa SSL automaticamente se o servidor suportar;
# para exigir SSL, use 'sslmode=require' na DSN (sem desligar a validação de cert).
```

---

### A4. Race condition — checkout duplicado / assinaturas repetidas

**Arquivo:** `main.py:156-207` + `database.py:294-314`

`criar_checkout` sempre insere uma nova linha `mei_assinaturas` com `status='pendente'`, sem verificar se o cliente já possui uma assinatura pendente/ativa, e sem idempotência. Dois cliques rápidos no botão "Assinar" (ou duplo POST) geram:
- 2 preferências no Mercado Pago;
- 2+ linhas `pendente` para o mesmo `cliente_id` (o webhook depois atualiza apenas a última via `obter_assinatura_cliente`).

**Correção sugerida (impedir duplicidade + tratar erro da MP):**

```python
@app.post("/api/assinatura/checkout")
async def criar_checkout(req: AssinaturaRequest):
    existente = await database.obter_assinatura_cliente(req.cliente_id)
    if existente and existente["status"] in ("pendente", "ativa"):
        raise HTTPException(status_code=409,
            detail="Ja existe uma assinatura pendente ou ativa para este cliente")

    async with httpx.AsyncClient() as client:
        resp = await client.post(..., json={...})
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Falha ao criar preferencia no Mercado Pago")
    dados = resp.json()
    if not dados.get("init_point"):
        raise HTTPException(status_code=502, detail="Preferencia sem init_point")

    await database.criar_assinatura({...})
    return {"sucesso": True, "checkout_url": dados["init_point"], ...}
```

---

### A5. Performance — `/api/resumo-anual` faz 24+ consultas (N+1)

**Arquivo:** `main.py:824-871`

```python
for mes in range(1, 13):
    vendas_mes_dados = await listar_vendas(mes=mes, ano=ano)     # 1 query
    despesas_mes_dados = await listar_despesas(mes=mes, ano=ano) # 1 query
```

São **24 consultas** mais 12 chamadas a `calcular_das`. Com tabelas crescente, isso degrada o endpoint.

**Correção sugerida:** 2 consultas agregadas (uma por tabela) + agrupamento em Python:

```python
# database.py
async def somar_por_mes(tabela: str, ano: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT SUBSTRING(data FROM 1 FOR 7) AS mes, SUM(valor) AS total "
            f"FROM {tabela} WHERE data LIKE $1 GROUP BY mes",
            f"{ano}-%"
        )
    return {int(r["mes"][-2:]): r["total"] for r in rows}
```

Depois iterar os 12 meses montando o dict sem novas queries.

---

### A6. Performance — `/api/faturamento-anual` faz 12 consultas

**Arquivo:** `main.py:874-894`

```python
for mes in range(1, 13):
    vendas_mes_dados = await listar_vendas(mes=mes, ano=ano)  # 12 queries
```

Mesma correção da A5 (uma query `SUM(valor) ... GROUP BY`).

---

### A7. Webhook do Mercado Pago sem autenticação da assinatura

**Arquivo:** `main.py:210-239`

O webhook aceita qualquer POST e usa `metadata.cliente_id` (enviado pelo cliente no checkout) para ativar a assinatura do banco. Não valida:
- o cabeçalho `X-Signature` (assinatura HMAC do Mercado Pago);
- que o `payment_id` pertence realmente a um checkout deste app;
- `external_reference` / `preference_id` da assinatura existente.

Um atacante pode falsificar um webhook e ativar o plano PRO sem pagar (o gate de plano é apenas visual — ver A8).

**Correção sugerida:** validar o `X-Signature` (HMAC-SHA256 com a secret) e conferir se o `external_reference`/`metadata` bate com uma assinatura pendente antes de ativar:

```python
from fastapi import Header
import hashlib, hmac

@app.post("/api/webhook/mercadopago")
async def webhook_mercadopago(request: Request, x_signature: str = Header(None)):
    # 1) Verificar assinatura HMAC do MP
    # 2) Buscar pagamento, conferir status == "approved"
    # 3) Conferir payment.external_reference == "cliente_{id}" e que existe assinatura pendente
    ...
```

---

### A8. Plano PRO não é imposto no backend (qualquer dado acessível sem auth)

**Arquivo:** `main.py` (todos os endpoints de produtos/vendas/despesas/clientes)

Não há autenticação nem autorização. `static/app.js:1041` apenas esconde o formulário de checkout visualmente. Uma pessoa com acesso à UI (ou via API direta) usa todos os recursos "PRO" sem pagar. É decisão de produto, mas do ponto de vista de segurança deve-se ao menos autenticar `cliente_id` e impedir `cliente_id=0` global (ver B2).

---

## MÉDIO — correção programada

### M1. `atualizar_cliente` apaga e recria o registro (perde ID / não transacional)

**Arquivo:** `main.py:702-719`

```python
existente = await obter_cliente(cliente_id)
if not existente:
    raise HTTPException(status_code=404, ...)
await excluir_cliente(cliente_id)   # DELETE
cliente = await criar_cliente({...}) # INSERT com NOVO id
```

Isso:
- muda o `id` do cliente (quebra vínculos com vendas `cliente_id`, que ficam órfãos);
- não é atômico — se o INSERT falhar, o cliente desapareceu;
- perde `criado_em` original.

**Correção sugerida:** usar `UPDATE` (existe `listar_clientes`/`obter_cliente`, mas não há `atualizar_cliente` no `database.py` — implementar):

```python
# database.py
async def atualizar_cliente(cliente_id: int, dados: dict) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
            UPDATE mei_clientes SET nome=$1, telefone=$2, email=$3,
              data_aniversario=$4, endereco=$5, observacoes=$6,
              produto_preferido=$7, periodicidade=$8 WHERE id=$9
        """, dados['nome'], dados.get('telefone'), dados.get('email'),
             dados.get('data_aniversario'), dados.get('endereco'),
             dados.get('observacoes',''), dados.get('produto_preferido'),
             dados.get('periodicidade'), cliente_id)
        return await obter_cliente(cliente_id)
```

`main.py:702` passa a chamar `atualizar_cliente` em vez de `excluir+criar`.

---

### M2. `/api/clientes/{id}/compras` carrega a tabela inteira em memória

**Arquivo:** `main.py:729-747`

```python
todas_vendas = await listar_vendas()          # SELECT * sem filtro
compras = [v for v in todas_vendas if v.get("cliente_id") == cliente_id]
```

Carrega **todas** as vendas de todos os clientes para filtrar em Python.

**Correção sugerida:** filtrar no banco.

```python
# database.py
async def listar_vendas_por_cliente(cliente_id: int) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mei_vendas WHERE cliente_id=$1 ORDER BY id DESC", cliente_id)
        return [dict(r) for r in rows]
```

---

### M3. Tratamento de erro que esconde falhas — `_calcular_dias_validade`

**Arquivo:** `main.py:407-413`

```python
def _calcular_dias_validade(data_validade: str) -> int:
    try:
        ...
    except:          # bare except engole TODA exceção
        return None
```

- `except:` sem tipo captura até `KeyboardInterrupt`/`SystemExit`;
- retorna `None` (que foge do type hint `-> int`) e esconde qualquer erro de parse;
- `data_validade` malformatada (ex.: `"31/02/2025"`, `"abc"`) cai silenciosamente em "indefinido".

**Correção sugerida:**

```python
from datetime import date
def _calcular_dias_validade(data_validade: str) -> int | None:
    try:
        data_val = datetime.strptime(data_validade, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return (data_val - date.today()).days
```

---

### M4. Uso de `print` em vez de logging

**Arquivo:** `database.py:115` (`print("[DB] Tabelas mei_* criadas...")`) e nenhum logging estruturado em `main.py`.

Sem logger configurado, erros em endpoints assíncronos não ficam registrados de forma inspecionável em produção.

**Correção sugerida:** configurar `logging` no módulo:

```python
import logging
logger = logging.getLogger("calculadora_mei")

logger.info("Tabelas mei_* criadas/verificadas")
# nos except:
logger.exception("Falha ao ...")
```

---

### M5. Checkout com taxa/valor desatualizado e sem tratamento de preço dinâmico

**Arquivo:** `main.py:22` (`PRECO_PRO_MENSAL = 9.90`) e `static/app.js` (efeito no `calcularEficiencia` com `das = 150`). Valores mágicos hardcoded aparecem em dois lugares (backend e frontend); qualquer ajuste precisa ser feito em ambos.

---

### M6. Upload de foto sem validação de tipo/tamanho

**Arquivo:** `main.py:520-541`

```python
ext = os.path.splitext(arquivo.filename)[1] if arquivo.filename else ".jpg"
...
shutil.copyfileobj(arquivo.file, buffer)
```

- não valida extensão/content-type (pode subir scripts/HTML);
- não limita tamanho (arquivos gigantes);
- `arquivo.filename` vem do cliente (controle sobre o nome).

**Correção sugerida:** validar `content_type` contra uma lista permitida (jpeg/png/webp), limitar tamanho (ex.: 2 MB) lendo o `UploadFile`, e gerar sempre um nome aleatório (já faz via `uuid`).

---

### M7. Webhook grava data como string inconsistente

**Arquivo:** `main.py:235`

```python
"data_inicio=NOW()::TEXT"
```

Grava timestamp TEXT com timezone em coluna definida como `TEXT` (`database.py:110`). Torna comparações/filtros por data frágeis. Preferir colunas `TIMESTAMP/DATE` reais ou padronizar formato `YYYY-MM-DD`.

---

### M8. `clientes_aniversario_mes` quebra com datas inválidas/NULL

**Arquivo:** `database.py:282-289`

```python
rows = await conn.fetch(
    "SELECT * FROM mei_clientes WHERE EXTRACT(MONTH FROM data_aniversario::DATE) = $1",
    mes_atual)
```

Se qualquer `data_aniversario` for texto não-conversível (ex.: `"15/07/1990"` ou `"abc"`), o cast `::DATE` lança erro **na query inteira** → endpoint `/api/clientes/aniversarios` retorna 500. Não há tratamento de erro nem filtro de formato.

**Correção sugerida:** validar no cadastro (M3) e/ou tornar a query resiliente:

```python
rows = await conn.fetch("""
    SELECT * FROM mei_clientes
    WHERE data_aniversario ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
      AND EXTRACT(MONTH FROM data_aniversario::DATE) = $1
""", mes_atual)
```

---

### M9. Sem `UPDATE` para despesas/produtos parciais e PUT de substituição total

- `PUT /api/produtos/{id}` (`main.py:488`) exige o objeto inteiro (todos os campos de `ProdutoRequest` são obrigatórios), então um PUT parcial quebra com 422. O frontend sempre envia o objeto completo, mas a API é frágil para consumidores externos. Considerar PATCH ou campos opcionais.

---

## BAIXO — melhoria opcional

### B1. Código morto / endpoints placeholders

- `_gerar_codigo_barras_texto` (`main.py:433-436`) nunca é chamado.
- `/api/scan-codigo` (`main.py:549-555`) é um placeholder ("integração com IA pendente"), mas o frontend (`app.js:777-811`) executa scanner real que só preenche o campo — a API não é usada.
- `obter_meses_restantes_ano` (`calculadora.py:208-211`) não é referenciado em lugar nenhum.
- `/api/alertas` (`main.py:347`) e `/api/tabela-das` (`main.py:357`) não parecem consumidos pelo frontend atual.

### B2. `cliente_id = 0` global para assinaturas

`static/app.js:1027` envia `cliente_id: 0`, e `verificarPlano` consulta sempre `/api/assinatura/0`. Isso significa que **todas** as assinaturas são vinculadas ao mesmo pseudo-cliente — duas pessoas assinando se sobrescrevem/cancelam. Deve-se atrelar a um identificador real do usuário (criar/login) em vez de `0`.

### B3. `dentro_do_teto` usa projeção `faturamento * 12`

`calculadora.py:103-104` define o teto como `faturamento * 12 <= 81000`, o que é uma heurística enganosa: o limite real é sobre o **faturamento acumulado do ano**, e o DAS é fixo e independente do faturamento. Um mês de R$ 8.000 marca "fora do teto" mesmo que o ano esteja longe do limite. Considerar usar o faturamento acumulado real nos resumos (via query agregada da A5/A6) em vez de projeção.

### B4. Constantes duplicadas no frontend

`static/app.js:641` repete `TETO_ANUAL = 81000`. Sempre que o teto mudar (reajuste anual), é fácil esquecer de atualizar em um dos lugares. Sugere-se consumir de `/api/tabela-das` ou uma variável global única.

### B5. CORS `allow_origins=["*"]` com `allow_credentials=True`

`main.py:49-54` — combinar * (wildcard) com credenciais é inválida/insegura segundo a especificação de CORS e expõe a API a qualquer origem. Restringir à origem do app (ex.: `https://calculadora-mei.onrender.com`) quando houver credenciais.

---

## Bugs lógicos / casos de borda adicionais

1. **Cálculo do vencimento do DAS (semântico, `calculadora.py:106-113`).** O código usa `datetime(ano, mes, 20)` como vencimento do mês informado. O DAS de competência N vence no dia 20 do mês **seguinte**. Conforme o uso (o usuário informa o mês do faturamento), a data exibida pode estar 1 mês adiantada. Validar qual competência o app declara atender e ajustar `DIA_VENCIMENTO`/mês de vencimento conforme.
2. **`simular_cenarios` calcula DAS de forma arbitrária (`calculadora.py:143-145`).** Usa `meses_no_teto = int(81000 / faturamento_mensal)` e só a tabela "servico". O DAS do MEI é **fixo por mês** (independe do faturamento) e deveria ser `12 × valor_das_da_atividade`. O cálculo atual subestima/erra para todos os cenários. Sugere-se usar `12 * (TABELA_DAS_2025[atividade]["inss"] + ...)`.
3. **`roi_meses = investimento / (lucro_liquido / 12)`** (`calculadora.py:152`) — `investimento_inicial = 2000` é um valor mágico arbitrário não configurável.
4. **`atualizar_produto` com PUT total** — ao reenviar um produto que tinha foto, se o payload não traz `foto_url`, a foto é sobrescrita com `None`. Idem para `estoque` etc.
5. **`upload_foto_produto` pode apagar informação** — atualiza o produto com o dict `produto` completo vindo de `obter_produto` + `foto_url`, mas `atualizar_produto` usa `dados.get('categoria','servico')` etc. e o dict vem de `obter_produto` que contém todas as colunas, então está ok, porém frágil por depender do shape completo do row.
6. **`listar_vendas`/`listar_despesas` com `LIKE` e sem índice** — `data LIKE '2025-08%'` faz full scan e colunas `data` são TEXT sem índice. Para volume relevante, indexar (`CREATE INDEX ... ON mei_vendas(data)`).
7. **`/api/health` consulta o banco a cada chamada** — para health check em render pode acionar conexões desnecessárias; aceitável, mas considerar cache curto.

---

## Ordem de correção recomendada

1. **A1** — Valores da tabela DAS (finanças/cobrança correta).
2. **A2** — Rotacionar senha + remover credencial do repo (segurança).
3. **A4 + A7** — Checkout duplicado + webhook sem assinatura (dinheiro/fraude).
4. **A5 + A6** — Performance dos endpoints anuais (banco compartilhado com SISGERSA).
5. **A3** — TLS.
6. **M1/M2/M3/M8** — Bugs de integridade e erros escondidos.
7. **Demais M/BAIXO** conforme prioridade de produto.

---

*Este relatório é apenas uma auditoria. Nenhum arquivo de código foi alterado.*
