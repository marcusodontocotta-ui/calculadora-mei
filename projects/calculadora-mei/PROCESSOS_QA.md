# Auditoria Final de PROCESSOS - Calculadora MEI

- **Build avaliado:** `817387c` (HEAD do repo, `main`). Deploy: `dep-da8faj0ae00c73cp9ba0` (live em https://calculadora-mei.onrender.com)
- **Data:** 2026-08-28 | **Equipe:** PROCESSOS (leitura de código local em `projects/calculadora-mei/` + testes HTTP em produção)
- **Natureza:** somente leitura/report. **Nenhum código foi alterado.**
- **Metodologia:** revisão de `main.py`, `database.py`, `static/app.js`, `templates/index.html`, `render.yaml`, `QA_PRODUCAO.md` + testes reais HTTPS de produção (contas QA criadas, **nenhum pagamento foi feito**; cupom TESTE100 validado até o `checkout_url`).

> **ALERTA PRELIMINAR (P0):** o comportamento de produção **não corresponde ao código do repositório em `817387c`** para o endpoint `/api/plano`. Detalhes nas Rupturas R1-R3. Qualquer veredito sobre o build fica condicionado à confirmação do código efetivamente em execução no Render.

---

## 1. Mapa do funil (10 etapas, landing → "PRO ativo")

| # | Etapa | Onde (código) | Estado |
|---|-------|---------------|--------|
| 1 | Landing: calculadora DAS + alertas públicos, sem login | `GET /` index.html; `POST /api/calcular-das`, `/api/alertas` | ✅ |
| 2 | Interesse PRO → seção `#plano-pro`, form `#proCheckoutForm` | index.html:1068-1138 | ✅ |
| 3 | Cadastro/Login (nome/email/senha → PBKDF2 + sessão 30d) | `main.py:413-470`, `database.py:178-240` | ✅ |
| 4 | `POST /api/assinatura/checkout` (com `cupom` opcional) → cria preferência MP + assinatura `pendente` no banco → `checkout_url` | `main.py:503-587`, `database.py:463-473` | ✅ (com ruptura R10/R12) |
| 5 | Redireciona para o checkout MP; `auto_return: approved`; `back_urls` → `/?pagamento=sucesso|pendente|erro` | `main.py:556-562` | ✅ |
| 6 | Webhook `POST /api/webhook/mercadopago`: consulta o pagamento na MP (sem `x-signature`), idempotência por `payment_id` UNIQUE | `main.py:590-662`, `database.py:536-550` | ⚠️ (R12, R7) |
| 7 | Ativação: `registrar_pagamento` + `ativar_assinatura` → `status='ativa'`, `data_fim=+30d` | `database.py:507-533` | ⚠️ (R4, R5) |
| 8 | **Safenet:** job de reconciliação a cada 300s (prod): expira `data_fim` vencida + procura pagamento aprovado por `external_reference=usuario_N` para assinaturas `pendente` | `main.py:249-322`; `render.yaml:20-21` (`RECONCILIACAO_INTERVALO_SEG=300`) | ⚠️ (R6, R7) |
| 9 | Retorno do usuário: `?pagamento=sucesso` → `verificarPlanoRealtime()` (poll de /api/plano, 4s, máx 90s) + `verificarPlano()` no load/login | `app.js:1500-1581` | ❌ (R1, R2, R11) |
| 10 | Estado PRO ativo: `#proStatus` "Seu plano PRO esta ativo!" + checkout escondido. Vencimento → `status='vencida'` → checkout liberado p/ recompra | `app.js:1519-1525`, `main.py:721-724` | ❌ (R4, R5, R9, R13v) |

**Confirmações positivas (itens que o funil acerta):**
- (a) Duplo clique sequencial → **`ja_pendente` funciona** (testado em prod, ver Evidências). Race real de concorrência existe (R10).
- (b) Usuário paga mas webhook não chega → **reconciliação cobre** (c/ ressalvas R6/R7).
- (c) Aba fechada antes de voltar → **polling 90s + recheck no load/login cobrem**, porém **não há botão "Consultar"** e a janela de 90s cobre só PageView única (R11).
- (d) Limite estourado em lote → **não há CONSTRAINT**: check-then-insert não atômico (R9). Duplicação em concorrência é possível.

---

## 2. Pontos de ruptura (severidade P0/P1/P2)

### P0

**R1 — Produção: `GET /api/plano` retorna HTTP 500 para usuário cadastrado SEM assinatura.**
Reproduzido 6x em 4 contas QA independentes (~1s por resposta, corpo vazio). O endpoint é a **fonte de verdade do front** (`verificarPlano`, `verificarPlanoRealtime`). Novo usuário free logado = erro 500 em todo load. `/api/auth/me` responde 200 (free) no mesmo usuário → o 500 é específico da rota.

**R2 — Produção: `GET /api/plano` retorna `ativo=true / plano=pro` para assinatura `pendente` (SEM pagamento).**
Reproduzido 4x (assina- tura status `pendente` contida na própria resposta). Consequência no funil: após criar checkout e voltar, `verificarPlanoRealtime` exibe "Seu plano PRO esta ativo! ✅" **mesmo sem pagamento** e `verificarPlano` **esconde o checkout** → usuário que não pagou acredita que ativou, não conclui a compra e não consegue tentar de novo pela UI. `/api/auth/me` e o gate real de CRUD seguem `free` (produto 17 → 422), i.e. o PRO **não é concedido de fato** — o indicador é que está errado, e é o indicador que o usuário vê.

**R3 — Drift de produção vs repositório: o código em execução não é o `817387c` (nem o `060802a`).**
Com o código do repo, `_assinatura_ativa` (main.py:221-230) retorna `False` para `pendente` e `ver_plano` (main.py:695-724) responde 200 para usuário sem assinatura. Produção faz o oposto nos dois casos — incluindo `renovacoes` presente na resposta, que só existe no branch `if ativa`. Conclusão: existe deploy/hotfix **não versionado** (ou instância antiga servindo). Todo o restante desta auditoria de produção fica sob suspeita até o owner identificar QUAL código está no Render.

### P1

**R4 — Código: expiração por `data_fim` pode encobrir PRO vencido (naive vs aware datetime).**
`ativar_assinatura` grava `data_fim` com `datetime.now(timezone.utc)` (**aware**, database.py:513-514) mas `_assinatura_ativa` compara com `datetime.now()` (**naive**, main.py:228) → `TypeError` → `except: return True`. Ou seja, assinatura `ativa` com `data_fim` passado continua avaliada como ativa até o job marcar `vencida` (janela de até 300s + dependência do job estar rodando). Se o `_loop_reconciliacao` parar (erro, reinício, multiplos workers), o usuário vencido mantém PRO sem pagamento por tempo indeterminado. A mensagem de "Assinatura expirada" (main.py:721-723) só aparece se `status='vencida'`.

**R5 — Funcional: renovação antecipada é IMPOSSÍVEL (bug do `ja_ativa`) + `data_fim` não acumula + métrica de renovação incorreta.**
- `criar_checkout` bloqueia com `ja_ativa` quando existe assinatura `ativa` (main.py:506-508) → PRO ativo **não gera novo checkout** → não há como pagar a renovação antes do vencimento. Hoje o usuário só renova após virar `vencida` (vira FREE no processo, fica sujeito aos limites 15/20/100/100 e corre risco de recompra com cupom reaplicável).
- `data_fim = agora + 30d` (database.py:514): renovar nunca estende o período vigente — **perde os dias restantes** do ciclo anterior.
- `renovacoes` é incrementada por **linha** da assinatura (database.py:522-533); como cada recompra cria uma nova row `pendente` (criar_assinatura faz INSERT), `renovacoes` reza 0 por ciclo → a métrica de renovação exibida em `/api/plano` não reflete fidelidade do usuário.
- ✅ Usuário `vencida` consegue criar checkout normalmente (fluxo de recompra funciona).

**R6 — LGPD (persiste): não existe exclusão de conta nem exportação de dados.**
Grep em todo o projeto: sem `DELETE /api/auth/conta`, sem export, sem função `excluir_usuario`. O único "excluir" é de itens de negócio (produtos/vendas/despesas/clientes). O titular não consegue exercer os arts. 9/18 da LGPD. `cancelar_assinatura` só cobre `status='ativa'`. Pior: a Política de Privacidade **continua afirmando "Nao coletamos dados pessoais" e "nao ha o que excluir"** (privacidade.html:35,39,59) — agora o sistema coleta nome/e-mail/senha (PBKDF2)/negócio → afirmação falsa = vies de transparência (art. 6º VI) + base para sanção.

**R7 — Fluxo: assinatura `pendente` abandonada trava o checkout para sempre (JA_PENDENTE eterno).**
Não há expiração/cancelamento de `pendente` (`expirar_assinaturas` só toca `status='ativa'`; `cancelar_assinatura` exige `ativa`). Usuário que abandona o checkout MP nunca mais consegue gerar novo checkout (R8a do `ja_pendente`) → fica preso em free sem como tentar pagar de novo pela UI. Precisa de botão "cancelar pendência" ou expiração da pendência com reemissão.

### P2

**R8 — Reconciliação: NÃO cobre pagamento aprovado sem assinatura no banco.**
O `payments/search` por `external_reference` só roda para assinaturas já `pendente` (main.py:262-271). Se o POST à MP criou a preferência mas o INSERT de `mei_assinaturas` falhou (DB/rede pós-checkout), o pagamento aprovado fica órfão: o webhook registra `mei_pagamentos` "sem_assinatura" e **não ativa nada** (main.py:643-649), e a reconciliação nunca o enxerga (não há pendente). Dinheiro cobrado sem PRO e sem recuperação. Cobertura incompleta da safenet.

**R9 — Reconciliação/Webhook: não confere `transaction_amount` nem título/item (e sem `x-signature`).**
Qualquer pagamento `approved` com `external_reference`/`metadata.usuario_id` correspondente ativa o PRO, independente do valor (R$ 0,01, R$ 9,90 ou outro) e do cupom. `x-signature` **não é validada** (main.py:590) — mantém o vetor de ativação fraudulenta apontado na auditoria anterior. Idempotência por `payment_id` UNIQUE cobre reentrada webhook/reconcilição (OK).

**R10 — Concorrência: duplo clique real → 2 checkouts (check-then-insert sem constraint).**
Sequencialmente o `ja_pendente` segura (testado). Mas dois POST simultâneos podem passar do `if pendente` antes do INSERT (sem UNIQUE em `mei_assinaturas(usuario_id)` em status pendente) → 2 preferências + 2 assinaturas pendentes → risco de dupla cobrança. Mesmo padrão (não atômico) nos limites de produtos/clientes/vendas/despesas: **lote no limite pode estourar** (contar→inserir com corrida).

**R11 — Front: mensagem de expirado nunca aparece + sem botão "Consultar".**
`verificarPlano` ignora `data.mensagem` (só usa `data.ativo`). A mensagem "Assinatura expirada. Renove..." do backend não é renderizada. Não existe botão de re-consulta manual; se a confirmação chegar após os 90s do polling, o usuário só percebe ao recarregar.

**R12 — Suporte/contato: somente `mailto` no footer (index.html:1198).**
Sem WhatsApp, sem formulário, sem página de suporte. FAQ existe e cobre DAS (index.html:1145-1176), mas **nada sobre conta/PRO/pagamento/reembolso/cancelamento/renovação** — exatamente os temas de maior fricção do funil pago. Termos/privacidade usam e-mails distintos (contato@ / privacidade@) sem evidência de monitoramento.

**R13 — Operac.: sessões e pendências sem limpeza + sem observabilidade da reconciliação.**
`mei_sessoes` cresce sem poda (validação na leitura, mas rows antigos permanecem). Tokens são gravados em texto puro (database.py:138-144) — se o DB vazar, sessões são forjáveis (senhas estão seguras: PBKDF2 100k iterações + salt por usuário — confirmado). A reconciliação só loga em stdout (sem relatório/endpoint de pendências para o dono inspecionar o que foi ou deixou de ser ativado). `ADMIN_SECRET` está setado (render.yaml:18-19, gerado) e sem token → 403 (testado); o **teste com o segredo real continua N/T**.

---

## 3. Recomendações (por prioridade)

1. **(Imediato)** Reproduzir/identificar o build no Render (log/deploy/console) e alinhar produção com o repo `817387c`. Sem isso, nenhuma medição de produção é confiável. Em seguida, corrigir `ver_plano` (500 p/ sem assinatura) e o `_ativa_se_vigente` para `pendente`→`False`, e cobrir `/api/plano` com testes de contrato no QA.
2. **(Alta)** Corrigir R4: usar data tz-aware em toda comparação (`datetime.now(timezone.utc)` e `fromisoformat`, ou normalizar para UTC) e **falhar com expirado** em vez de `except: return True`.
3. **(Alta)** Renovação (R5): liberar checkout para `ativa` (re-cobrança) ou criar job de cobrança recorrente; `data_fim` deve estender o período vigente (`agora + dias_restantes`) e `renovacoes` deve contar por usuário.
4. **(Alta)** `pendente` abandonada (R7): expirar/purgar pendências com `data_criacao` antiga e adicionar ação "cancelar pendência" na UI — senão trancará pagadores reais.
5. **(Média)** Reconciliação (R8): varrer também `mei_pagamentos` com `assinatura_id IS NULL` e pagamentos aprovados sem row correspondente; validar valor esperado (R9); validar `x-signature` no webhook.
6. **(Média)** LGPD (R6): endpoint autenticado de exclusão de conta (cascade de sessões/assinaturas/dados) + export; reescrever a Política de Privacidade (coleta real, finalidade, base legal, compartilhamento MP/SISGERSA, retenção, direitos, contato) e ajustar Termos (PRO/cobrança/cancelamento/reembolso já para 12 meses promocionais).
7. **(Média)** Concorrência (R10): UNIQUE parcial em `mei_assinaturas(usuario_id) WHERE status='pendente'` + transação com `SELECT ... FOR UPDATE` nos limites de plano.
8. **(Baixa)** Front (R11): renderizar `data.mensagem`; adicionar "Consultar novamente" no banner; FAQ PRO/suporte WhatsApp (R12); job de limpeza de `mei_sessoes` e relatório simples de reconciliação (R13).

---

## 4. Checklist de lance (pronto / não pronto)

| Item do funil | Estado |
|---|---|
| Landing + cálculo DAS público | ✅ PRONTO |
| Cadastro/login/logout (PBKDF2, sessão 30d, `me` ) | ✅ PRONTO |
| Isolamento de dados por usuário em todos os CRUDs | ✅ PRONTO |
| Limites FREE encerrando com 422 (excluído quorum em corrida) | ✅ PRONTO (R10 aberto) |
| Upload validado (magic bytes + 2MB + extensão ⇒ 415/413) | ✅ PRONTO (P2 PNG/JPEG conhecida) |
| Cupom TESTE100 → checkout R$ 0,01 | ✅ PRONTO |
| Idempotência sequencial do checkout (`ja_pendente`) | ✅ PRONTO |
| Webhook processa `payment` approved + idempotência por `payment_id` | ⚠️ PARCIAL (sem `x-signature`, sem valor) |
| Reconciliacão 300s (loop) + endpoint manual com `ADMIN_SECRET` setado | ⚠️ PARCIAL (não cobre órfãos; teste real N/T) |
| Expiração automática 30d (`vencida` + mensagem) | ⚠️ PARCIAL (bug R4 + dependência do job) |
| `/api/plano` como fonte de verdade do front | ❌ NÃO PRONTO (500 free + pendente→pro + drift) |
| Renovação de plano | ❌ NÃO PRONTO (bloqueada p/ ativos, perde dias, métrica errada) |
| LGPD: exclusão de conta / exportação | ❌ NÃO PRONTO |
| Política de Privacidade e Termos realistas | ❌ NÃO PRONTO (política afirma não coletar dados) |
| Suporte (mailto) + FAQ | ⚠️ PARCIAL (sem WhatsApp, FAQ só DAS) |
| Tratamento de `pendente` abandonada | ❌ NÃO PRONTO |

---

## 5. QA existente (avaliação metodológica)

`QA_PRODUCAO.md`: **39 PASS / 0 FAIL / 3 N/T** — resultado confiável para o que testou, com 3 lacunas de metodologia:

1. **`/api/plano` NÃO consta no QA** (só `/api/auth/me` e o legado `/api/assinatura/{cliente_id}`). Foi exatamente a rota onde produção está quebrada → a suíte precisava de contratos para: free sem assinatura, pendente, vencida, ativa, cancelada, e uso dos campos `ativo/plano/assinatura.status/mensagem`.
2. Os **3 N/T precisam mesmo do dono**: (8.2) reconciliação com o `ADMIN_SECRET` real; (9.5) limites PRO 500/500/2000/2000; (6.2/7/…) expiração real de 30d + webhook com pagamento real (autorizar ao menos um checkout TESTE100 de R$ 0,01). Sem eles, o loop de ativação/renovação fica sem prova de fogo no ambiente real.
3. A suíte não detectaria R1-R5 (bug em `data_fim` naive/aware, `renovacoes` por row, `pendente` eterna) — recomendar casos de limite para "vencida sem job" e "duplo POST concorrente".

---

## 6. Evidência dos testes em produção (2026-08-28)

- `GET /api/health` → 200 `healthy`, version 2.0.0, `assinaturas_ativas=1`.
- `GET /api/tabela-das` → 200 com **`ano=2026`** (fix de 817387c aplicado no campo).
- Cadastro QA (4 usernames distintos) → 201, token válido; `me` → `autenticado=true, plano=free`.
- Checkout TESTE100 → `sucesso=true, valor_final=0.01`, `checkout_url` MP válido. 2ª/3ª chamadas → `sucesso=false, motivo=ja_pendente` (idempotência sequencial OK).
- `GET /api/plano` sem assinatura → **HTTP 500** (6x, ~1s, em usuários distintos).
- `GET /api/plano` com assinatura `pendente` → **`ativo=true, plano=pro, assinatura.status=pendente, renovacoes=0`** (4x). Mesmo usuário: `me` → free (inconsistência interna de produção).
- Limite FREE: 16º produto → HTTP 422 (gate real respeita FREE mesmo com `/api/plano` errado).
- `GET /api/plano` sem token → 401. `POST /api/admin/reconciliar` sem token → 403.
- A partir do 5º teste em rajada o app passou a responder `/api/health` e `/api/auth/me` com timeout (HTTP 0) — indicativo de cold start/stress do free tier do Render; não classificado como bug.

---

## 7. Resumo final e veredito

**Rupturas encontradas:** 3 P0 independentes: **(R1)** `/api/plano` 500 para usuário sem assinatura em produção; **(R2)** `/api/plano` ativa a bandeira PRO para assinatura `pendente` em produção (falso "PRO ativo" no funil); **(R3)** produção ≠ repo `817387c` (drift de build). Mais 4 P1: **(R4)** comparação naive/aware esconde expiração; **(R5)** renovação antecipada impossível + `data_fim` não acumula + `renovacoes` por row; **(R6-LGPD)** sem exclusão/export de conta e política afirmando "não coletamos dados"; **(R7)** pendência abandonada bloqueia novos checkouts para sempre. 6 P2 (reconciliação não cobre pagamento órfão, sem `x-signature`/valor, corridas de check e limites sem constraint, front sem mensagem de expirado/botão consultar, suporte só mailto, operacional/observabilidade).

**O que está comprovado funcionando:** cadastro/login (PBKDF2), isolamento por usuário, limites FREE (422), upload seguro, cupom TESTE100→checkout 0,01, idempotência sequencial do checkout (`ja_pendente`), webhook idempotente por `payment_id`, reconciliação com loop 300s + `ADMIN_SECRET` gerado, expiração por SQL (com a ressalva R4).

**VEREDITO: NO lançamento do funil pago de produção como está — com base no código do repo, corrigir R4, R5, R6 e R7 antes de lançar; e, com base na produção, o ambiente atual NÃO está pronto (R1/R2/R3 invalidam a fonte de verdade do plano).** A infraestrutura de "conta + planos" está madura, mas o **fluxo de monetização recorrente (renovação) e o endpoint `/api/plano` são os dois pontos que impedem o "PRO ativo" de ocorrer de forma confiável.** QA segue com 39 PASS, porém sem cobertura de `/api/plano`; os 3 cenários N/T dependem do dono (secret, limites PRO, pagamento real) e **devem ser executados com o código correto em produção** antes do próximo lance.