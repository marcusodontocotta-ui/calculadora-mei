# Auditoria Final de Segurança & LGPD — Pós-Deploy (Build 817387c)

**Aplicação:** Calculadora MEI — https://calculadora-mei.onrender.com
**Commit auditado:** `817387c` (em produção)
**Data:** 27/08/2026
**Equipe:** Segurança & LGPD — **somente leitura/report. Nenhum código foi alterado.**
**Método:** Chamadas HTTP reais em produção + revisão de código local em `C:\Users\Marcus Cotta\Documents\Default Project\cupula-gestao\projects\calculadora-mei` + inspeção do histórico git + API Render (env-vars verificadas com valores **mascarados** no relatório).

---

## Resumo executivo

O deploy do build `817387c` implementou corretamente as **mitigações de autenticação, isolamento por usuário, limites de plano, webhook idempotente e upload validado por magic bytes** — confirmadas em produção. **Porém, permanecem 2 achados P0**: (1) a **credencial real do banco de dados permanece commitada no histórico git e no working tree**, e — crítica — a `DATABASE_URL` de produção usa **exatamente a mesma credencial**, portanto nunca foi rotacionada; (2) a **Política de Privacidade ainda declara falsamente que "não coleta dados pessoais"**, contradizendo o sistema de contas agora ativo (violação do princípio de transparência da LGPD).

**Contagem de achados: P0 = 2 · P1 = 4 · P2 = 3**

**Veredito final: NÃO APROVADO** — o P0 de credencial rotacionável é bloqueante; a política de privacidade P0 deve ser corrigida antes de considerarmos o lançamento em conformidade.

---

## Tabela de achados (novos/confirmados)

| # | Severidade | Descrição | Evidência | Recomendação |
|---|---|---|---|---|
| S1 | **P0** | Credencial real do PostgreSQL commitada no código e em **todo o histórico git** (11/11 commits), e a `DATABASE_URL` de produção usa a **mesma** credencial (nunca rotacionada). Acesso ao banco compartilhado SISGERSA por quem tiver acesso ao repo. | `database.py:13` contém `postgresql://sisgersa_app:ixnU2…@dpg-…/sisgersa`. Env var Render `DATABASE_URL` = mesmo valor (verificado na API, **valor mascarado aqui**). `git grep` achou a credencial em todos os commits. `.gitignore` **não existe**. | **Urgente:** rotacionar a senha do `sisgersa_app` (ou gerar nova credencial) e atualizar a env var; **remover o fallback** em `database.py:13` (ler só de `os.environ` e `raise` se ausente); criar `.gitignore`; rodar Gitleaks/TruffleHog; **reescrever o histórico** (BFG/filter-repo) para remover a credencial. |
| L1 | **P0** | Política de Privacidade afirma falsamente que "não coleta dados pessoais", contradizendo o sistema de contas (nome/e-mail do usuário) e clientes (PII). | `templates/privacidade.html:35` ("Nao coletamos dados pessoais") e `:39` ("NAO coleta, armazena ou transmite dados pessoais"). App agora cadastra/login de usuários (main.py:413) e armazena clientes (nome/telefone/email/endereço/aniversário). | Reescrever a página descrevendo dados coletados, finalidade, base legal (art. 7º), retenção, compartilhamento (Mercado Pago, banco) e direitos do titular (art. 18) + DPO identificável. Corrigir antes do lançamento. |
| X1 | **P1** | Stored/self-XSS via `innerHTML` com dados do usuário sem escape (produto, venda, despesa, cliente). Com contas, o vetor exige autenticação, mas dados não são sanitizados e executam para quem visualizar. | `static/app.js`: produto `704-726` (nome/descrição), venda `824-829` (descrição/cliente), despesa `958-961` (descrição), cliente `1272-1290` (nome/tel/email/obs), aniversariante `1333-1340`. | Usar `textContent`/`createElement` ou função `escapeHtml()`; nunca interpolar campos do usuário em `innerHTML`; sanitizar no backend. |
| F1 | **P1** | Bug funcional de upload: o arquivo é lido em `conteudo` para validação e depois **reescrito a partir de `arquivo.file` já no EOF** → todas as fotos gravadas ficam **vazias (0 bytes)**. | Produção: upload de PNG fake com magic bytes retornou 200 com `foto_url`, mas o arquivo servido tem `Content-Length: 0`. `main.py:1033` (`read()`) vs `main.py:1053` (`copyfileobj(arquivo.file,...)`). | Escrever `conteudo` (já em memória) no arquivo, não `arquivo.file`. Revalidar `conteudo` como backend da escrita. |
| S2 | **P1** | Webhook MP sem validação de assinatura `x-signature`. O fluxo consulta a MP antes de ativar (mitiga parte), mas o endpoint aceita POST não assinado. | Teste prod: `POST /api/webhook/mercadopago {"type":"payment","data":{"id":"QA-FAKE-889922"}}` → 200 `{"sucesso":false,"processado":false,"motivo":"mp_inacessivel"}`. **Nada ativado; nenhum dado vazado.** `main.py:590-662` não valida `x-signature`. | Validar `x-signature` (rsa_sha256 + template `ts,v1`) e conferir valor/`external_reference` antes de ativar. |
| S3 | **P1** | CORS excessivamente permissivo. | `main.py:81-82`: `allow_origins=["*"]` + `allow_credentials=True`. | Restringir a origins reais e remover `allow_credentials` (sem cookies). |
| P2.1 | **P2** | `GET /api/health` vaza métricas internas (nº de assinaturas ativas, tabela DAS). | Produção: `GET /api/health` → 200 com `assinaturas_ativas`, versão, tabela DAS. | Oculta contagens internas em endpoint público ou move para autenticado. |
| P2.2 | **P2** | Conexão SSL do banco com verificação desabilitada (`CERT_NONE`). | `database.py:39-43`. | Usar `sslmode=verify-full`. |
| P2.3 | **P2** | Sem rate limiting nos endpoints de escrita. | Revisão de código (nenhum middleware de limite). | Adicionar rate limit (slowapi) por IP/rota. |

**Confirmado OK em produção (testes):**

| Teste | Resultado |
|---|---|
| `GET /api/health` | **200** healthy |
| `GET /api/plano` sem token | **401** (`Token nao fornecido`) |
| `GET /api/produtos` sem token | **401** |
| `GET /api/produtos/{id}` com token B em item do A | **404** (isolamento OK; A vê seu próprio item → 200) |
| `POST /api/webhook/mercadopago` payment_id falso | **200, processado=false, sem ativação e sem vazamento** |
| Upload `.html` disfarçado de `image/png` | **415** rejeitado |
| Upload `.svg` (`image/svg+xml`) | **415** rejeitado |
| Upload PNG com magic bytes | **200** — porém arquivo **vazio (0 bytes)** (bug F1); servido com `Content-Type: image/png` (extensão forçada `.png`) |
| `POST /api/admin/reconciliar` sem token | **403** (`Nao autorizado`) |

---

## Status dos achados ANTIGOS

| Achado antigo (SEGURANCA_LGPD.md) | Status | Comentário |
|---|---|---|
| 🔴 Credencial DB commitada (`database.py:13`) | ❌ **Aberto (P0)** | Env var `DATABASE_URL` setada no Render, mas o **fallback hardcoded permanece** com a **mesma credencial viva**; está em todo o histórico git. A mitigação "env var setada" **não** elimina a exposição nem rotaciona a senha. |
| 🔴 Ausência de autenticação/autorização | ✅ **Migrado** | Contas + tokens + escopo por `usuario_id`; isolamento confirmado (404 entre usuários). |
| 🔴 Webhook sem validação de assinatura | ⚠️ **Parcialmente migrado** | Agora idempotente + consulta a MP antes de ativar (teste: falso não ativa). `x-signature` ainda não validada (S2). |
| 🔴 Upload sem validação | ✅ **Migrado (com ressalva)** | Validação por magic bytes (jpg/png/webp) + máx 2 MB + extensão forçada servida como imagem. **Porém** bug F1 grava arquivo vazio. |
| 🔴 Stored XSS via `innerHTML` | ❌ **Aberto (P1)** | `app.js` ainda interpola sem escape em produtos/vendas/despesas/clientes. |
| 🟠 CORS permissivo | ❌ **Aberto (P1)** | `*` + `allow_credentials=True`. |
| 🟠 SSL banco `CERT_NONE` | ❌ **Aberto (P2)** | Ainda presente. |
| 🟠 Rate limiting | ❌ **Aberto (P2)** | Ainda não implementado. |
| 🟡 Health vaza métricas | ❌ **Aberto (P2)** | Ainda expõe `assinaturas_ativas`. |
| 🟡 Token MP padrão `TEST-xxx` | ✅ **Migrado** | `MP_ACCESS_TOKEN`/`MP_PUBLIC_KEY` reais definidos no Render (valores mascarados). |
| ✅ SQL Injection mitigado | ✅ **Migrado (manter)** | Todas as queries parametrizadas (`$1`). |
| 🔴 LGPD: política diz "não coleta dados" | ❌ **Aberto (P0)** | `privacidade.html:35,39` ainda falso com contas ativas. |
| 🔴 LGPD: sem mecanismo direitos do titular | ❌ **Aberto (P1)** | Sem exportar/excluir dados via interface. |
| 🟠 LGPD: política incompleta | ❌ **Aberto (P1)** | Sem base legal/compartilhamento/DPO identificável. |
| 🟠 Termos sem cláusulas PRO/cobrança | ❌ **Aberto (P2)** | Sem cancelamento/reembolso/foro. |

---

## Detalhes dos achados críticos

### P0 — S1: Credencial do banco commitada e jamais rotacionada
O fallback em `database.py:13` contém a connection string completa do banco **compartilhado SISGERSA**. Verificação via API Render (Authorization Bearer, **valor mascarado** neste relatório) confirmou que a variável `DATABASE_URL` na produção contém **exatamente o mesmo usuário/senha** do fallback. Ou seja: a senha `sisgersa_app` é pública no repositório (todas as revisões via `git grep` retornaram a string) e é a mesma usada em produção. A "mitigação" de ter a env var setada não é eficaz — qualquer pessoa com acesso ao repositório pode conectar diretamente ao banco.

### P0 — L1: Política de Privacidade incorreta
`templates/privacidade.html:35` "Nao coletamos dados pessoais. Sua privacidade e garantida." e `:39` "NAO coleta, armazena ou transmite dados pessoais". Com o sistema de contas, a aplicação **coleta e armazena** nome e e-mail do usuário cadastrado, além de dados de clientes (nome, telefone, e-mail, endereço, aniversário). A página permanece desatualizada (data "26 de agosto de 2025"). Violação do princípio de transparência (art. 6º, VI LGPD). **Sugestão de correção textual** (substituir o bloco "Resumo" e seção 1/2/3/5):
> "A Calculadora MEI coleta e armazena dados pessoais necessários ao funcionamento da conta e do cadastro de produtos, vendas, despesas e clientes (nome, e-mail, telefone, endereço), bem como dados de pagamento tratados pelo Mercado Pago. Os dados são tratados conforme a LGPD (Lei 13.709/2018): finalidade específica do serviço, base legal de execução de contrato e legítimo interesse, com retenção apenas pelo período necessário. Você pode acessar, corrigir, exportar ou solicitar a exclusão dos seus dados entrando em contato com o Encarregado de Dados (privacidade@calculadoramei.com.br)."

---

## Veredito final

**NÃO APROVADO** — com ressalvas. As medidas de autenticação, isolamento, limites de plano, idempotência do webhook e validação de upload **funcionam em produção** e estão corretas para os testes executados. Entretanto, **2 achados P0 bloqueiam a aprovação**:
1. **S1** — credencial viva do banco commitada e não rotacionada;
2. **L1** — Política de Privacidade falsa (contradição LGPD) ainda em produção.

Recomendação: corrigir **S1** (rotacionar + remover fallback + limpar histórico) e **L1** (reescrever a política) antes de considerar o build aprovado; endereçar os P1 (XSS via innerHTML, upload 0-byte, x-signature, CORS) no próximo ciclo.

**Contagem final: P0 = 2 · P1 = 4 · P2 = 3.**

*Relatório de auditoria — somente leitura. Nenhum arquivo do projeto foi modificado. Nenhum commit foi criado.*
