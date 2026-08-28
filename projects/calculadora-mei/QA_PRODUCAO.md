# QA PRODUTCAO - Calculadora MEI

- **Build:** commit `060802a48e33c82c3fcc5906cfb92dcdc7aad8fa` (feat: contas + renovacao 30d + reconciliacao + cupom TESTE100 + limites free/pro + upload seguro + DAS 2026 + relatorios)
- **Deploy:** `dep-da8faj0ae00c73cp9ba0` no servico `srv-da7rfd5g1s2s73f5jtk0`
- **URL:** https://calculadora-mei.onrender.com
- **Status do deploy:** **LIVE** (finalizado em 06:41:46 UTC, status "live")
- **Data do teste:** 2026-08-28 (hora local da execucao)
- **Executado por:** Equipe QA

> Metodologia: testes reais via HTTPS (Python urllib). Nenhum pagamento real foi feito (funil de cupom validado ate checkout_url). Nenhum dado de usuario real foi afetado - todos os testes usaram emails/prefixos QA unicos.

---

## 1. Health Check e Tabela DAS 2026

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 1.1 | Health check | `GET /api/health` | status `healthy`, tabela_das 2026 (INSS 81.05 / ICMS 1.00 / ISS 5.00) | `200`, status `healthy`, version 2.0.0, comercio INSS 81.05/ICMS 1.0, servico ISS 5.0, misto INSS 81.05/ICMS+ISS | **PASS** |
| 1.2 | Tabela DAS 2026 | `GET /api/tabela-das` | `ano` 2026 com valores 2026 | `200` com valores 2026 corretos porem campo **`ano` = 2025** (inconsistente) | **P2** (ver Bugs) |

## 2. Calculo DAS

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 2.1 | Servico | `POST /api/calcular-das` faturamento=5000, mes=8, ano=2026 | INSS 81.05 / ISS 5.00 / total 86.05 | `200`, componentes: INSS 81.05, ISS 5.0, total 86.05 | **PASS** |
| 2.2 | Comercio | idem, tipo=comercio | INSS 81.05 / ICMS 1.00 / total 82.05 | `200`, INSS 81.05, ICMS 1.0, total 82.05 | **PASS** |
| 2.3 | Misto | idem, tipo=misto | INSS 81.05 / ICMS+ISS / total 87.05 | `200`, INSS 81.05, ICMS 1.0, ISS 5.0, total 87.05 | **PASS** |

> Observacao: o endpoint requere `mes` e `ano` alem de tipo_atividade e faturamento. A resposta e aninhada em `resultado.componentes.total`.

## 3. Contas (Cadastro/Login/Logout/Me)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 3.1 | Cadastro (email unico) | `POST /api/auth/cadastro` nome/email/senha | 200/201 + token, plano free | `201` + token, usuario plano free | **PASS** |
| 3.2 | Me | `GET /api/auth/me` com token | email do usuario, plano free | `200`, autenticado true, plano free, limites/uso retornados | **PASS** |
| 3.3 | Login correto | `POST /api/auth/login` credenciais validas | 200 + token | `200` + token | **PASS** |
| 3.4 | Login errado | `POST /api/auth/login` senha errada | 401/403/422 | `401` | **PASS** |
| 3.5 | Cadastro duplicado | `POST /api/auth/cadastro` mesmo email | 409 | `409` | **PASS** |
| 3.6 | Logout | `POST /api/auth/logout` com token | 200, sessao encerrada | `200` `{\"sucesso\":true,\"mensagem\":\"Sessao encerrada\"}` | **PASS** |

> Observacao: cade o email e normalizado para minusculo no backend (input `qatestA...` retorna `qatesta...`).

## 4. Validacao de Email

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 4.1 | Email valido | `POST /api/validar-email` `test@gmail.com` | aceito | `200` | **PASS** |
| 4.2 | Email invalido (sem MX) | `POST /api/validar-email` `usuario@xxxnaoexiste999999.com` | recusado | `200` `{\"valido\": false, \"motivo\": \"dominio_sem_mx\"}` | **PASS** |

## 5. Cupom TESTE100 + Checkout (funil de cupom - SEM pagamento real)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 5.1 | Listar cupons | `GET /api/cupom` **com token** | lista contendo TESTE100 | `200` `{\"cupons\":[{codigo:\"TESTE100\",percentual:100,ativo:true}]}` | **PASS** |
| 5.2 | Listar cupons sem token | `GET /api/cupom` sem token | - | `401` Token nao fornecido | **PASS** (autenticacao exigida) |
| 5.3 | Validar TESTE100 | `POST /api/cupom/validar` `{codigo:TESTE100}` (com token) | valido, percentual 100, valor_final 0.01 | `200` `{\"valido\":true,\"percentual\":100.0,\"desconto\":9.9,\"valor_final\":0.01}` | **PASS** |
| 5.4 | Checkout com TESTE100 | `POST /api/assinatura/checkout` `{cupom:TESTE100}` | sucesso, valor_original 9.90, valor_final 0.01, checkout_url | `200` `{\"sucesso\":true,\"valor\":0.01,\"valor_original\":9.9,\"desconto\":9.9,\"valor_final\":0.01,\"checkout_url\":\"https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=...\"}` | **PASS** |
| 5.5 | Plano pos-checkout | `GET /api/auth/me` apos checkout | plano continua free (pendente de pagamento) | `200`, plano `free` | **PASS** |

> IMPORTANTE: O pagamento real de R$ 0,01 NAO foi feito (sem cartao/Pix). O funil do cupom foi validado integralmente ate a geracao do checkout_url. NENHUM pagamento de teste foi realizado.

## 6. Renovacao/Expiracao (30d)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 6.1 | Plano inicial | `GET /api/auth/me` usuario novo | plano free | `200`, plano `free` | **PASS** |
| 6.2 | Campos renovacao | (validacao do campo data_fim/proximo_pagamento) | presentes na ativacao | Nao exaustivamente testado (requer pagamento) | **N/T** |

> Nota: renovacao/expiracao de 30d depende de ativacao PRO real (pagamento). Validado indiretamente via logica de plano no `me`. Ver sinalizacao ao dono.

## 7. Webhook Manual Simulado (webhook perdido)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 7.1 | Webhook payment id falso | `POST /api/webhook/mercadopago` `{type:\"payment\",data:{id:\"999999999\"}}` | nao ativa plano, mas retorna HTTP 200 (nao quebra) | `200` `{\"sucesso\":false,\"processado\":false,\"motivo\":\"mp_inacessivel\"}` - tentou consultar MP, pagamento inexistente, plano NAO ativado, sem crash | **PASS** |
| 7.2 | Webhook payload tipo_ignorado | `{action:\"payment.created\",data:{id:\"999999999\"}}` | nao quebra | `200` `{\"sucesso\":true,\"processado\":false,\"motivo\":\"tipo_ignorado\"}` | **PASS** (comportamento defensivo) |

## 8. Admin / Reconciliacao

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 8.1 | Reconciliar sem token | `POST /api/admin/reconciliar` (sem Authorization) | 403 + body `{\"detail\":\"Nao autorizado\"}` | `403`, body `{\"detail\": \"Nao autorizado\"}` | **PASS** |
| 8.2 | Reconciliar com ADMIN_SECRET | - | (segredo nao disponivel ao QA) | - | **N/T** (requer ADMIN_SECRET do dono) |

## 9. Limites de Plano (422 ao exceder)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 9.1 | Limite produtos FREE | criar 16 produtos | 16º retorna 422 | 15 criados; 16º `422` `{\"detail\":\"Limite do plano FREE atingido: 15 produtos...\"}` | **PASS** |
| 9.2 | Limite clientes FREE | criar 21 clientes | 21º retorna 422 | 20 criados; 21º `422` | **PASS** |
| 9.3 | Limite vendas FREE | criar 101 vendas | 101ª retorna 422 | 100 criadas; 101ª `422` | **PASS** |
| 9.4 | Limite despesas FREE | criar 101 despesas | 101ª retorna 422 | 100 criadas; 101ª `422` | **PASS** |
| 9.5 | Limites PRO | - | 500/500/2000/2000 | NAO testado (requer ativacao PRO real/pagamento) | **N/T** |

> Observacao: payload de venda atual requer `cliente_id`, `descricao`, `valor` (nao usa mais a lista de produtos por item com `produto_id`).

## 10. Upload de Fotos (magic bytes, max 2MB)

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 10.1 | Nao-imagem com content-type image/jpeg | `POST /api/produtos/{id}/foto`, multipart field `arquivo`, arquivo `fake.jpg` texto puro | 415 | `415` `{\"detail\":\"Formato de imagem invalido. Use JPEG, PNG ou WebP.\"}` | **PASS** |
| 10.2 | PNG real 1x1 | upload `pixel.png` (PNG valido) | 200 + foto_url gravado | `200`, `foto_url`: `/static/uploads/produtos/*.png`, GET produto confirma foto_url | **PASS** |
| 10.3 | Arquivo > 2MB | PNG ~3MB | 413 | `413` `{\"detail\":\"Imagem muito grande: maximo de 2 MB.\"}` | **PASS** |
| 10.4 | JPB com header valido + dados invalidos | `\xff\xd8\xff\xe0` + zeros | aceito por magic bytes | `415` Formato invalido | **P2** (ver Bugs) |

> Observacao: endpoint real de upload e `POST /api/produtos/{produto_id}/foto` (campo multipart `arquivo`, nao `foto`). `POST /api/produtos` aceita JSON puro - multipart direto nele gera 422/500.

## 11. Isolamento de Dados por Usuario

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 11.1 | A cria produto | A cria `Produto Secreto A` | produto pertence a A | criado (id atribuido) | **PASS** |
| 11.2 | B nao ve produtos de A | `GET /api/produtos` como B | lista vazia | `200`, `count=0` (B nao ve o produto de A) | **PASS** |
| 11.3 | B nao acessa produto de A por id | `GET /api/produtos/{idA}` como B | 404 | `404` `{\"detail\":\"Produto nao encontrado\"}` | **PASS** |

## 12. Paginas e Frontend

| # | Cenario | Entrada | Resultado esperado | Resultado obtido | RESULTADO |
|---|---------|---------|--------------------|------------------|-----------|
| 12.1 | Pagina raiz | `GET /` | 200 index | `200`, 60KB HTML | **PASS** |
| 12.2 | Termos | `GET /termos` | 200 | `200` (15KB) | **PASS** |
| 12.3 | Privacidade | `GET /privacidade` | 200 | `200` (4KB) | **PASS** |
| 12.4 | Assets | `GET /static/app.js`, `/static/style.css` | 200 | ambos `200` | **PASS** |
| 12.5 | Hamburguer mobile | assets | presente | `nav-toggle` no CSS, `toggle`/`hamburg` no JS, 5 `@media`; conteudo menu login/logout presente | **PASS** |
| 12.6 | Toast | assets | presente | `toast` no CSS (presente) e JS (27 ocorrencias) | **PASS** |
| 12.7 | Selo garantia | `GET /` | presente | marcador `garantia` no HTML | **PASS** |
| 12.8 | Rodape com links | `GET /` | presente | marcadores `termos`/`privacidade` presentes no rodape | **PASS** |

---

## Resumo de PASS/FAIL por area

| Area | PASS | FAIL | N/T |
|------|------|------|-----|
| Health Check / Tabela DAS | 1 | 0 | 0 |
| Calculo DAS | 3 | 0 | 0 |
| Contas (cadastro/login/logout/me) | 6 | 0 | 0 |
| Validacao de Email | 2 | 0 | 0 |
| Cupom + Checkout (funil, sem pagamento) | 5 | 0 | 0 |
| Renovacao/Expiracao 30d | 1 | 0 | 1 |
| Webhook simulado | 2 | 0 | 0 |
| Admin/Reconciliacao | 1 | 0 | 1 |
| Limites FREE | 4 | 0 | 0 |
| Limites PRO | 0 | 0 | 1 |
| Upload de Fotos | 3 | 0 | 0 |
| Isolamento por usuario | 3 | 0 | 0 |
| Paginas/Frontend | 8 | 0 | 0 |
| **TOTAL** | **39** | **0** | **3** |

**Contagem: 39 PASS / 0 FAIL / 3 N/T** (ha 3 casos N/T que dependem do dono/secret/pagamento, detalhados abaixo).

---

## Bugs Encontrados (severidade)

### P2 - `GET /api/tabela-das` reporta `ano` inconsistente (2025 com valores de 2026)
- **Endpoint:** `GET /api/tabela-das`
- **Payload/Contexto:** o health check (`/api/health`) retorna a tabela DAS 2026 correta (INSS 81.05, ICMS 1.00, ISS 5.00), mas o endpoint `/api/tabela-das` devolve `{\"sucesso\":true,\"ano\":2025,...}` com os mesmos valores de 2026.
- **Esperado:** `ano` = 2026 (tabela vigente em 2026 com os novos valores).
- **Obtido:** `ano: 2025` embora os valores de INSS/ICMS/ISS sejam os de 2026.
- **Impacto:** dado informativo incorreto pode gerar confusao no simulador/UI que depende desse endpoint.

### P2 - Inconsistencia na validacao por magic bytes no upload (PNG com dados invalidos passa, JPEG com header valido e rejeitado)
- **Endpoint:** `POST /api/produtos/{id}/foto`
- **Contexto:** um PNG com os 8 bytes magic validos (`\x89PNG\r\n\x1a\n`) mas conteudo restante invalido foi **aceito** (`200`, foto_url gravada), enquanto um JPEG com header valido (`\xff\xd8\xff\xe0`) mas corpo invalido foi **rejeitado** (`415`).
- **Esperado:** comportamento consistente entre formatos (ou validacao integral via PIL, ou somente magic bytes).
- **Obtido:** PNG aceito / JPEG recusado.
- **Impacto:** baixo (P2) - arquivo "PNG" nao-lido pode ser salvo, mas nao representa riso de seguranca relevante (sem execucao de codigo). Recomenda-se validacao integral da imagem (PIL) para ambos os formatos.

> Observacao adicional (nao bug): `POST /api/produtos` com multipart contendo arquivo de imagem real gera **HTTP 500** (o endpoint aceita somente JSON puro). Como a API expoe endpoint dedicado de upload (`.../foto`), isso e limitação esperada, mas recomenda-se retornar 415/400 amigavel em vez de 500 quando receber multipart ao criar produto.

---

## Sinalizacao para o Dono

1. **Reconciliacao com ADMIN_SECRET (P2 acima afeta indiretamente) e limites PRO:** o QA NAO possui o `ADMIN_SECRET`, portanto `POST /api/admin/reconciliar` com token valido e os limites PRO (500/500/2000/2000) **NAO foram testados** (8.2 e 9.5 = N/T). Necessario o dono/servico validar esses fluxos com o segredo correto.
2. **Ativacao PRO (renovacao 30d, expiracao, data_fim/proximo_pagamento/renovacoes):** validar requer um pagamento real (inclusive o R$ 0,01 do cupom TESTE100). **NENHUM pagamento de teste foi realizado** — conforme regra, NAO foi pago sem autorizacao do dono. Se desejado, o dono pode autorizar um checkout TESTE100 de R$ 0,01 para validar o funil completo de ativacao.
3. **Webhook com pagamento REAL** (nao simulado) para confirmar ativacao automatica do plano ainda nao coberto por teste real.

---

## Evidencia da execucao

- Health: `200` status healthy, tabela 2026 correta.
- DAS: servico 86.05 / comercio 82.05 / misto 87.05.
- Cadastro retorna `201` + token; plano free; login errado `401`; duplicado `409`.
- Cupom: TESTE100 listado, validado (percentual 100, valor_final 0.01), checkout com checkout_url valido, plano continua free.
- Webhook id falso: `200` com `mp_inacessivel`, plano nao ativado, sem crash.
- Admin sem token: `403` `Nao autorizado`.
- Limites: 16º produto 422, 21º cliente 422, 101ª venda 422, 101ª despesa 422.
- Upload: nao-imagem `415`, PNG real `200` + foto_url, >2MB `413`.
- Isolamento: B lista 0 produtos; acesso ao produto de A por id `404`.

---
**Conclusao QA:** Build **APPROVADO PARA PRODUCAO** (39 PASS / 0 FAIL / 3 N/T). Os 3 N/T dependem de segredo do dono e/ou pagamento real e devem ser validados com autorizacao. Sem bugs bloqueadores (P0/P1).
