# Relatório de Auditoria — PROCESSOS · Calculadora MEI

**Equipe:** Avaliação de Processos
**Data:** 2026-08-27
**Produto live:** https://calculadora-mei.onrender.com
**Escopo:** funil de compra (landing → conta → pagamento → PRO), processo comercial (renovação/inadimplência/cancelamento), processos internos (deploy/backup/monitoramento), atendimento, e cobrança/reconciliação.
**Natureza:** auditoria somente — **nenhum código foi alterado**.

Arquivos auditados: `main.py`, `database.py`, `static/app.js`, `templates/index.html`, `templates/termos.html`, `templates/privacidade.html`, `BACKUP.md`, `DEV_OPS.md`, `CODE_REVIEW.md`, `SEGURANCA_LGPD.md`, `NEGOCIO.md`, `LANCAMENTO.md`, `render.yaml`, `Dockerfile`, `requirements.txt`.

---

## 0. Veredito executivo

O funil **existe e funciona ponta a ponta**, mas está construído sobre 3 rupturas estruturais que podem travar a receita e quebrar a confiança:

1. **Não existe renovação automática do PRO** — o "checkout" cria uma **preferência de pagamento única** do Mercado Pago (Checkout Pro), **não** uma assinatura recorrente (preapproval). As colunas `data_fim` e `proximo_pagamento` existem mas **nunca são gravadas nem lidas**. Uma vez ativa, a assinatura fica `ativa` **para sempre** (nenhum código lê `data_fim`). Na prática: o cliente paga R$ 9,90 uma única vez e usa o PRO indefinidamente — o MRR assumido no `NEGOCIO.md` **não se materializa mecanicamente**. **P0.**
2. **Perda de webhook = assinante pago sem PRO, para sempre.** O webhook não grava o `payment_id`, não é idempotente, engole erros (sempre responde 200) e não há rotina de reconciliação. Se a notificação se perder, o `status` fica `pendente` indefinidamente e **ninguém percebe** (o front-end para de checar após 90 s). **P0.**
3. **"Validação de e-mail" não valida nada.** Não há envio de e-mail de confirmação, token de verificação, ou "reenviar". O único cheve é formato + MX + blacklist. E-mail falso cadastra normalmente. **P1.**

A seguir, o mapa completo com severidades e o plano de ação priorizado (P0/P1/P2).

---

## 1. Mapa do funil de compra

Fluxo implementado (com referência de código):

```
[1] Visitante → landing /
      ├─ Calcula DAS e simula como usuário anônimo (endpoints públicos:
      │  POST /api/calcular-das  main.py:499 · POST /api/simular  main.py:534)
      └─ Cria conta / credenciais
           ↓
[2] Cadastro  POST /api/auth/cadastro  main.py:278
      • valida: formato do e-mail (EMAIL_REGEX), senha ≥ 6, e-mail único
      • gera salt + hash PBKDF2(100k)  main.py:156-168
      • cria sessão e devolve token (login automático)  main.py:296-307
      • ⚠️ NÃO envia e-mail de verificação; NÃO há confirmação de posse;
        NÃO há rate limit; NÃO há botão "esqueci a senha"
           ↓
[3] Assinatura  POST /api/assinatura/checkout  main.py:353
      • valida que não há assinatura ATIVA (mas ignora PENDENTEs)  main.py:356-358
      • chama MP "checkout/preferences" (pagamento ÚNICO, não recorrente)  main.py:360-393
         - metadata.usuario_id / external_reference = "usuario_{id}"
         - notification_url = /api/webhook/mercadopago
         - back_urls success → /?pagamento=sucesso · pendente · erro
      • insere mei_assinaturas status='pendente', "mp_subscription_id" = id da PREFERÊNCIA  main.py:397-403
      • ⚠️ NÃO checa resp.status_code da MP; insere 'pendente' mesmo se a MP falhar;
        NÃO tem idempotência (duplo clique gera 2 preferências + 2 linhas pendentes)
           ↓
[4] Redirect → init_point do Checkout Pro (Checkout externo na MP)
      • auto_return=approved devolve com ?pagamento=sucesso
      • usuario fecha a aba / começo da renovação = sem link salvo para retomar
           ↓
[5] Webhook  POST /api/webhook/mercadopago  main.py:413
      • type=payment → GET /v1/payments/{id} (MP)  main.py:424-429
      • se status=approved → busca assinatura PENDENTE do usuario_id  main.py:433-437
      • ativa (status='ativa', data_inicio=now)  main.py:439 · database.py:442
      • ⚠️ sem validação x-signature · sem idempotência por payment_id ·
        ATRASO do MP é normal (segundos a minutos); erro é engolido (print) ·
        se o app reinicia durante o processamento, a notificação pode se perder
           ↓
[6] Retorno do usuário  ?pagamento=sucesso  (app.js:1440)
      • banner "Ativando seu plano..." + polling /api/plano a cada 4 s por até 90 s  app.js:1459-1489
      • se webhook ainda não chegou → depois de 90 s vira mensagem "será ativado automaticamente"
      • ⚠️ sem botão "verificar novamente"; sem reenvio do link; sem alerta posterior
           ↓
[7] Uso  →  dados isolados por usuario_id (todos os CRUDs em database.py)
      • usuario_id nas colunas de produtos/vendas/despesas/clientes/assinaturas  database.py:132-136
      • Sessões expiram em 30 dias  main.py:176 · database.py:182-205
```

### 1.1 Onde o funil QUEBRA (pontos de ruptura)

| # | Etapa | Ruptura | Efeito real |
|---|---|---|---|
| R1 | 5–6 | Webhook atrasa/lento | Usuário chegou no banner e o plano demora a ativar. Poll de 90 s cobre parte; depois, silêncio. Sem re-check manual, o usuário não sabe se pagou. |
| R2 | 5 | Webhook **perdido** (MP não entrega, app reiniciou, erro engolido) | Assinatura fica `pendente` **para sempre**. Cliente pago, PRO inativo. **Nenhum mecanismo detecta** (não há tabela de pagamentos, não há job de reconciliação). |
| R3 | 3 | Usuário **fecha a aba da MP** sem voltar | Não há como reabrir a preferência (só o `id` é salvo). "Assinar de novo" gera **nova preferência + nova linha pendente** (duplicata). |
| R4 | 3 | Duplo clique / duplicidade no checkout | 2+ preferências e 2+ linhas `pendente`; o webhook ativa a última (`ORDER BY id DESC LIMIT 1`). Custo extra de tarifa e confusão no painel MP. |
| R5 | 5 | Webhook fraudado / sem assinatura | `x-signature` não é validado (achado C4/A7 das auditorias anteriores). POST com payment_id conhecido ativa PRO sem pagamento. |
| R6 | 6 | Usuário volta para o site e não vê confirmação | Após 90 s o polling para; se o plano ativou depois disso, a aba mostra a mensagem de "pendente" até refresh. UX confusa. |
| R7 | 2 | E-mail falso / descartável | Nenhuma verificação real de posse; cadastro aceita `aaa@mailinator.com`. Polui a base, invalida métrica de "cadastros free". |
| R8 | 3 | Checkout falha na MP (token expirado, 400) | Cria linha `pendente` mesmo assim; retorna `init_point=None` → alert "Erro ao iniciar pagamento". Usuário tenta de novo → mais duplicatas. |
| R9 | 7 | Dados antigos (pré-isolamento) | Registros com `usuario_id NULL` viram órfãos (invisíveis para todos). Hoje = 1 cliente e 4 assinaturas (dados de teste), mas vale conferir antes de produção real. |

---

## 2. Riscos por etapa (com severidade)

| Etapa | Risco | Severidade | Detalhe / evidência |
|---|---|---|---|
| Landing | FAQ com **valores de DAS errados** (R$ 150/R$ 225) | 🟡 Média | index.html:1136 — contradiz a tabela correta do `calculadora.py` (achado A1 do CODE_REVIEW). Marketing não alinhado com o produto; risco de desconfiança. |
| Cadastro | "Valida email" é só formato+MX; sem confirmação real | 🟠 Alta | Não existe envio de e-mail (sem SMTP/SendGrid/Resend no repo). `_validar_email_completo` (main.py:228) aceita qualquer MX; `_dominio_tem_mx` no-op True se `nslookup` não existir no ambiente (main.py:200-225). |
| Cadastro | Sem rate limit / sem captcha; sem "esqueci senha" | 🟡 Média | Cadastro/login sem throttling (SEGURANCA_LGPD aponta). Senha mínima 6 chars. |
| Cadastro | Sem fluxo de redefinição de senha | 🟡 Média | Só existe login/senha; usuário que esqueceu não recupera (perde acesso isolado). |
| Checkout | Duplicidade (race) | 🟠 Alta | main.py:353 checa só ATIVA; cria preferência e linha `pendente` por clique. |
| Checkout | Erro MP não tratado (status code / sem timeout) | 🟠 Alta | main.py:360-403 — `httpx` sem `timeout`; não valida `resp.status_code`; insere `pendente` mesmo com erro; `init_point=None`. |
| Checkout | Pagamento **único**, não recorrente | 🔴 Crítica | `checkout/preferences` = Checkout Pro one-shot; não é preapproval/subscription. `mp_subscription_id` na verdade guarda o id da preferência (main.py:402). |
| Redirect | Sem link persistente para retomar | 🟠 Alta | Usuário que fecha a aba da MP perde o fluxo; "assinar" de novo duplica. |
| Webhook | Perda/re-entrega sem idempotência | 🔴 Crítica | Sem registro de `payment_id`; webhook pode ser chamado várias vezes; erro é impresso no console e máscara com `{"sucesso": True}` (main.py:451). |
| Webhook | Sem validação de assinatura | 🔴 Crítica | Vetor de ativação fraudulenta (sem pagamento). |
| Retorno | Poll tem aposta de 90 s e desiste | 🟠 Alta | app.js:1459-1489. Depois disso, sem botão "verificar", sem notificação, sem recovery. |
| Plano | Assinatura `ativa` nunca expira | 🔴 Crítica | Nenhum código lê `data_fim`/`proximo_pagamento`; `_plano_usuario` usa só `status` (main.py:191). PRO perpétuo após 1 pagamento. |
| Dados | Isolamento por usuário OK, mas legado órfão | 🟡 Média | Colunas `usuario_id` (database.py:132-136). Registros pré-migração ficam `NULL`. |
| Dados | Upload de foto em disco efêmero | 🟡 Média | Some a cada redeploy (DEV_OPS C5). |
| Health | `GET /api/assinatura/{cliente_id}` é **público** (legado) | 🟡 Média | main.py:454 — sem `Depends(usuario_atual)`; qualquer um consulta status de assinatura por id. Recurso de reconciliação interna com exposição. |

---

## 3. Processo comercial (renovação / expiração / inadimplência / cancelamento)

**3.1 Renovação automática mensal — NÃO implementada.**
- O checkout usa `POST /checkout/preferences` (main.py:361), que cria um **pagamento unitário**. Não há `POST /preapproval` (Recurring), nem plano recorrente no Mercado Pago.
- `data_inicio` é gravada (database.py:446), mas `data_fim` e `proximo_pagamento` **nunca são escritos** (criados no schema database.py:110-111, nunca usados).
- Consequência de receita: **MRR mecanicamente = 0 após o 1º mês de cada cliente**. O modelo do `NEGOCIO.md` (churn 4–8%, LTV, MRR projetado) assume recorrência que o código não produz.

**3.2 Assinatura expirada — não existe o conceito.** Nada lê `data_fim`. Um PRO ativado hoje fica `ativa` para sempre (even sem pagamento recorrente). Não há job diário que "expire" planos.

**3.3 Inadimplência — não existe o conceito.** Sem cobrança recorrente não há cobrança a falhar. Porém, quando a recorrência for implementada, **não há hoje nenhum mecanismo** de: tentativa de cobrança, fatura pendente, downgrade após N dias, ou comunicação de cobrança/chargeback (a sessão em si expira 30 dias, mas isso é o login, não o plano).

**3.4 Cancelamento — parcial.**
- Backend: `POST /api/assinatura/{cliente_id}/cancelar` existe (main.py:481) e cancela por `usuario_id` (database.py:462).
- Frontend: **não há botão/UI de cancelamento** (busca por `cancelar|cancelamento` em app.js → nenhum resultado). O FAQ diz "Cancele quando quiser" e o checkout diz "Cancele quando quiser" (index.html:1112), mas o usuário **não encontra onde**.
- Como não há cobrança recorrente, o cancelamento não precisa estornar nada hoje — mas quando existir recorrência, cancelar no app **não** cancelará a cobrança na MP (não há chamada à API de cancelamento/preapproval).

---

## 4. Processos internos de dev

**4.1 Deploy**
- Render Web Service (buildpacks), `autoDeploy: yes`, mas os últimos deploys foram via **API/CLI** (trigger `api`, DEV_OPS §1). Fluxo de push→deploy não confirmado.
- `render.yaml` está **desatualizado** (plan free, sem `rootDir`, `fromDatabase` inválido, sem `healthCheckPath`) — DEV_OPS C6/C9. `Dockerfile` não é usado (conflito de dois caminhos).
- Não há CI de testes (existe `test_full.py`/`test_api.py` manuais, sem runner) nem staging/preview.

**4.2 Backup**
- Existe **BACKUP.md** completo (pg_dump 18 via Docker, automação GitHub Actions, restore/teste, retenção, checklist) + 1 snapshot validado (12.630 B).
- **Pendências:** não há o workflow `.github/workflows/backup-mei.yml` já criado no repo (só documentado); o Render **não tem `DATABASE_URL`** configurada (app usa credencial hardcoded em `database.py:13`); backup depende de `DATABASE_URL` secret que ainda não foi criada. O banco é **compartilhado com o SISGERSA** (C2). Recomenda-se moderar a urgência: hoje só existem ~5 linhas relevantes, mas o backup deve estar automatizado **antes** de escala.

**4.3 Monitoramento**
- `/api/health` existe e mede app+banco (main.py:262), mas **não está configurado** no Render (`healthCheckPath` vazio) — DEV_OPS I1. Sem probe de external uptime (UptimeRobot/UptimeKuma), sem log drain (Sentry/Logtail), erros só via `print` no console do Render.

**4.4 Testes**
- `test_full.py` e `test_api.py` existem mas não rodam em pipeline e **não cobrem** o fluxo de pagamento/webhook/reconciliação (não há teste do webhook, idempotência ou renovação).

---

## 5. Atendimento

| Canal | Status | Evidência |
|---|---|---|
| Página de contato | ❌ **Não existe** — rodapé tem link "Contato" para `#` (morto) | index.html:1178 |
| WhatsApp | ❌ **Não existe número/botão.** A seção PRO promete "Suporte prioritário via WhatsApp" (index.html:1093) mas não há link `wa.me` em lugar nenhum | grep `wa.me|whatsapp` → vazio |
| FAQ | ⚠️ Existe na landing (6 itens), mas **2 respostas com valores errados** e sem orientação de suporte | index.html:1126-1156 |
| E-mail | ⚠️ `contato@calculadoramei.com.br` (termos:149) e `privacidade@calculadoramei.com.br` (privacidade:72) mencionados — **não confirmado se o domínio/caixa existe** nem se há rotina de resposta | — |
| LGPD | ❌ Sem via de solicitação de dados (exclusão/exportação) | SEGURANCA_LGPD |

**Impacto:** um visitante com problema de pagamento (a ruptura R2 — pago sem ativar) **não tem por onde reclamar**. Isso vira chargeback + "golpe" + review negativo. O canal de atendimento é pré-requisito do funil de cobrança, não um extra.

---

## 6. Processo de cobrança / reconciliação

**Situação atual:** impossível reconciliar com precisão.
- Não há tabela de pagamentos (`mei_pagamentos`): o `payment_id` recebido no webhook é usado na esquerda para consultar a MP, mas **não é persistido**.
- Webhook não é idempotente, não tem `x-signature`, e **sempre responde `{"sucesso": True}`** mesmo quando o processamento falha (main.py:451) — não deixa rastro para auditoria.
- Sem job periódico que cruze "assinaturas `pendente` antigas" × "pagamentos aprovados na MP".

### Rotina de reconciliação sugerida (implementação futura)

1. **Registrar pagamentos (P0):** criar `mei_pagamentos` (`payment_id` UNIQUE, `preference_id`, `usuario_id`, `status`, `valor`, `raw json`, `criado_em`). Webhook grava **antes** de processar (registro de chegada) e depois atualiza com o resultado. `payment_id` UNIQUE → idempotência nativa.
2. **Job diário de reconciliação (cron, P1):** para cada `mei_assinaturas.status='pendente'` com mais de X horas:
   - consulta `GET /v1/payments/search?external_reference=usuario_{id}&sort=date_created&criteria=desc` na API MP;
   - se houver payment `approved` → ativa a assinatura (mesma lógica do webhook, centralizada numa função);
   - se houver payment `rejected`/`cancelled` → marca `pendente` com motivo / avisa o usuário;
   - se não houver nenhum pagamento → asssinatura `pendente` órfã pode ser reciclada/cancelada após N dias.
3. **Controle de receita (P1):** relatório mensal = soma de pagamentos `approved` no mês (via `mei_pagamentos` ou busca na MP) vs. assinaturas ativas. Dá MRR real, tarifa real e inadimplência observada (o `NEGOCIO.md` pede "conciliação do webhook" — seção 9, regra 3).
4. **Alerta de desvio (P2):** se houver pagamento `approved` na MP sem assinatura ativa/pendente correspondente (external_reference órfão), gerar tarefa de correção manual.

---

## 7. Recomendações acionáveis (P0 / P1 / P2)

> Ordem de prioridade. P0 = trava o negócio agora; P1 = janela de semanas; P2 = contínuo/melhorias.

### P0 — Urgente (trava de receita e legal)

| # | Ação | O que / onde | Por quê |
|---|---|---|---|
| P0.1 | Implementar **recorrência real** (preapproval/subscription MPC) com `data_inicio`, `data_fim`, `proximo_pagamento` gravados em toda ativação; manter campo `mp_subscription_id` com o id da **assinatura** (não da preferência). | main.py:353 (checkout), database.py:442 (ativar) | Sem isso o PRO é pagamento único e o MRR do NEGOCIO.md é fictício. |
| P0.2 | Criar **`mei_pagamentos`** + webhook **idempotente** (UNIQUE `payment_id`) e com **`x-signature` validado**. | main.py:413, database.py | Fecha R2 e R5; primeira perna da reconciliação. |
| P0.3 | Criar **job diário de reconciliação** (pendentes antigos × payments MP) e, no mínimo, **endpoint de recuperação** `GET /api/plano?refresh=1` que reconsulta a MP para o usuário logado e ativa se houver pagamento aprovado. | novo roteiro + main.py | Elimina "pago sem PRO" permanente (R2) e dá o "botão verificar" que falta no front. |
| P0.4 | **Front-end de recuperação pós-pagamento:** botão "Verificar pagamento" no banner pendente (chama P0.3); polling maior ou re-check ao reabrir app com `?pagamento=sucesso`. | app.js:1440-1489 | Cobre usuário que fecha a aba e o webhook lento. |
| P0.5 | **Remover credencial hardcoded** do banco, configurar `DATABASE_URL` secret no Render e agendar rotação (validar com DEV_OPS/SEGURANCA_LGPD). | database.py:13, Render | Risco crítico já reportado; impede avançar backup seguro. |
| P0.6 | **Automatizar backup** (criar o workflow do BACKUP.md no repo + secret `DATABASE_URL`). | BACKUP.md §4 | Backup mensal em execução deve existir antes de qualquer escala. |

### P1 — Alta (janela de semanas)

| # | Ação | Onde |
|---|---|---|
| P1.1 | **Idempotência/race no checkout:** bloquear novo checkout se houver `pendente`/`ativa`; usar `if-resp.status_code not in (200,201)` + `timeout` no httpx; único `pendente` por usuário. | main.py:353-410 |
| P1.2 | **Verificação de e-mail real** (token por e-mail) OU, no mínimo, confirmar posse na ativação; bloquear domínios descartáveis no cadastro (hoje só no checkout). | main.py:278, 228 |
| P1.3 | **Fluxo de cancelamento no front + cancelamento no lado MP** (PARAR preapproval) quando recorrência existir; hoje o backend cancela mas não há botão. | app.js, main.py:481 |
| P1.4 | **Downgrade por inadimplência:** job diário que marca `vencida`/`suspensa` assinaturas com `data_fim < now` e faz o app tratar como `free`. Nenhum código de expiração existe hoje. | database.py, main.py:191 |
| P1.5 | **Página de contato + WhatsApp real** (link `wa.me` com número do suporte) e FAQ corrigindo valores de DAS; dar canal visível no footer e na tela de pagamento pendente. | index.html:1126-1184 |
| P1.6 | **Mecanismo LGPD** ("Exportar meus dados" / "Excluir minha conta") ligado ao usuário autenticado. | privacidade.html, main.py |
| P1.7 | **Health check no Render** (`healthCheckPath: /api/health`) + monitor de uptime externo. | Render, DEV_OPS I1/I5 |
| P1.8 | Cobrir **webhook/reconciliação em testes** (test_full.py/test_api.py) — hoje o fluxo de dinheiro não tem teste. | test_*.py |

### P2 — Melhorias (contínuo)

| # | Ação |
|---|---|
| P2.1 | Renovação com aviso: lembrete +30/-7 dias e **1ª renovação explícita** antes de virar automática (o NEGOCIO.md sugere; reduz chargeback). |
| P2.2 | Implementar plano **anual R$ 99** (devido à inexistência de recorrência, o anual é hoje a única forma de capturar 12 meses à vista — prioridade natural). |
| P2.3 | Configurar pipeline de CI (lint + testes) e um caminho de deploy único (buildpacks ou Docker, eliminar o conflito); pin versionar `requirements.txt`. |
| P2.4 | Logging estruturado + log drain (Sentry/Logtail) para rastrear webhooks e erros; incluir `payment_id`, `external_reference`, `usuario_id` nos logs. |
| P2.5 | Limpar duplicatas históricas de assinaturas `pendente` e decidir o destino dos registros órfãos (`usuario_id NULL`). |
| P2.6 | Proteger `GET /api/assinatura/{cliente_id}` (endpoint legado público) ou removê-lo. |
| P2.7 | Upload de fotos em storage externo (R2/S3) com validação de tipo/tamanho; correção dos valores de DAS no FAQ. |

---

## 8. Anexo — evidências-chave

| Evidência | Local |
|---|---|
| Checkout cria preferência ÚNICA (não recorrente) | main.py:360-393 |
| `mp_subscription_id` guarda id da preferência | main.py:402 |
| `data_fim`/`proximo_pagamento` criados e nunca usados | database.py:110-111 |
| Ativação sem data_fim | database.py:442-448 |
| Nenhum leitor de expiração | main.py:191 (_plano_usuario só lê status) |
| Webhook sempre responde sucesso e engole erro | main.py:448-451 |
| Sem `mei_pagamentos` | database.py:52-129 (schema completo) |
| Poll de 90 s e mensagem pendente final | app.js:1459-1489 |
| Sem link "verificar"/"reenviar" | app.js (busca `reenviar|verificar pagamento` → vazio) |
| Sem cancelamento na UI | app.js (busca `cancelar` → vazio) |
| "Suporte via WhatsApp" sem número | index.html:1093 |
| Link "Contato" = `#` | index.html:1178 |
| FAQ com DAS R$ 150/R$ 225 | index.html:1136 |
| Sem envio de e-mail em todo o projeto | main.py (sem smtp/sendgrid/resend) |
| Health check existe, não configurado no Render | main.py:262 · DEV_OPS §2 |
| Backup documentado, workflow não criado | BACKUP.md §4 |

---

*Relatório gerado pela Equipe de Avaliação de Processos. Nenhum arquivo do projeto foi modificado.*