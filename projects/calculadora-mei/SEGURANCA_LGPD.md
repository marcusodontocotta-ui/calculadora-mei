# Relatório de Auditoria — Segurança & Conformidade LGPD

**Aplicação:** Calculadora MEI (https://calculadora-mei.onrender.com)
**Data da auditoria:** 27/08/2026
**Arquivos auditados:** `main.py`, `database.py`, `calculadora.py`, `static/app.js`, `templates/index.html`, `templates/termos.html`, `templates/privacidade.html`, `render.yaml`, `Dockerfile`, `requirements.txt`
**Escopo:** vazões/credenciais, autenticação, webhook Mercado Pago, SQL Injection, upload de arquivos, política de privacidade, termos de uso e mecanismos de direitos LGPD.
**Natureza:** auditoria apenas — **nenhum código foi alterado**.

---

## Resumo executivo

A aplicação armazena dados pessoais (nome, telefone, e-mail, endereço, datas de aniversário de clientes) e dados financeiros (vendas, despesas, faturamento) de forma **global e sem autenticação**, e ainda assim sua Política de Privacidade afirma que **“não coleta dados pessoais”**. Essa divergência, somada a uma credencial real de banco de dados commitada no código, torna a situação de risco **crítica** — tanto do ponto de vista de segurança quanto de conformidade com a LGPD (Lei 13.709/2018).

| Área | Situação |
|---|---|
| Segurança de dados | **Crítica** — credencial real exposta + zero autenticação + XSS armazenado + upload inseguro |
| Webhook MP | Assinatura `x-signature` **não validada** |
| SQL Injection | **Mitigado** — consultas parametrizadas via asyncpg (`$1`) |
| LGPD | Política desatualizada/incorreta; sem mecanismos de direitos do titular |

---

## 1. Achados de SEGURANÇA

### 🔴 ALTO — Credencial de banco de dados commitada no código

- **Local:** `database.py:11-14`
- **Descrição:** O fallback de `DATABASE_URL` contém uma connection string real de produção filtrada contra um banco PostgreSQL compartilhado do SISGERSA (`sisgersa_app:ixnU2…` em `osg-…oregon-postgres.render.com/sisgersa`). A mesma credencial existe na cópia de deploy em `calculadora-mei-deploy/database.py:12`.
- **Impacto:** Qualquer pessoa com acesso ao repositório pode conectar-se diretamente ao banco e ler/escrever/apagar todos os dados do SISGERSA (não só da Calculadora MEI). A credencial é de fato “commitada” mesmo que o valor real não esteja no git — ela está no código-fonte distribuído.
- **Recomendação:**
  1. **Rotacionar imediatamente** a senha do usuário `sisgersa_app` (ou trocar a credencial inteira).
  2. Remover o fallback: ler **somente** de `os.environ.get("DATABASE_URL")` e falhar cedo (`raise`) se ausente.
  3. Criar `.gitignore` e usar variáveis de ambiente/config secret (Render/Heroku) para `DATABASE_URL`.
  4. Rodar scanner de segredos (Gitleaks/TruffleHog) no histórico e nos deploys futuros.

### 🔴 ALTO — Ausência total de autenticação/autorização (dados de todos expostos)

- **Local:** `main.py:441-727` (CRUD de produtos, vendas, despesas, clientes); `main.py:242-268` (assinaturas)
- **Descrição:** Todos os endpoints `/api/*` são públicos, sem login, sessão, token ou escopo por usuário. Não há “dono” dos dados: **todos os usuários compartilham o mesmo banco**. O front-end usa `cliente_id: 0` fixo (`app.js:1027`, `app.js:1043`).
- **Impacto:**
  - `GET /api/clientes` e `GET /api/clientes/{id}` expõem nome, telefone, e-mail, endereço e data de aniversário de **todos** os cadastrados.
  - `GET /api/vendas`, `/api/despesas`, `/api/resumo-mensal/anual` expõem finanças de todos.
  - `DELETE /api/clientes/{id}` permite a **qualquer pessoa excluir dados de terceiros** (integridade + LGPD: perda de dados sem base legal).
  - `GET /api/assinatura/{cliente_id}` revela status de assinatura de qualquer ID.
- **Recomendação:** Implementar autenticação por usuário (ex.: OAuth/GitHub, e-mail+senha com sessão ou JWT) e **escopar todas as queries** por `user_id` (adicionar coluna `mei_produtos.user_id`, etc.). Se a intenção é um app single-tenant embrionário, ao menos exigir autenticação básica + rate limiting até o multi-tenant.

### 🔴 ALTO — Webhook do Mercado Pago sem validação de assinatura `x-signature`

- **Local:** `main.py:210-239`
- **Descrição:** O endpoint `/api/webhook/mercadopago` lê o corpo JSON e ativa a assinatura **sem verificar o header `x-signature`** (nem a chave pública do Mercado Pago, nem o `id`/`merchant_order`/valor). Qualquer atacante pode `POST` com `{"type":"payment","data":{"id":<qualquer>}}`.
- **Impacto:** Ativação fraudulenta de assinaturas (Plano PRO sem pagamento), reprocessamento indevido e ruptura do fluxo de cobrança. É o vetor número 1 de fraude em integrações MP.
- **Recomendação:**
  1. Validar `x-signature` (rsa_sha256 + template `ts,v1`) conforme documentação do Mercado Pago **antes** de processar.
  2. Confirmar que o `payment_id` corresponde ao `external_reference`/`metadata` criado pelo próprio checkout e que `status == "approved"` veio da API (já faz a chamada de volta — manter) e verificar `transaction_amount`.
  3. Tornar o handler idempotente (mais de uma notificação por pagamento é esperado).

### 🔴 ALTO — Upload de fotos sem validação (arbitrário + XSS via arquivo servido)

- **Local:** `main.py:520-541`
- **Descrição:** `POST /api/produtos/{id}/foto` salva o arquivo como `/static/uploads/produtos/{uuid}.{ext}` **sem** limite de tamanho, **sem** validação de conteúdo/MIME, **sem** lista branca de extensões. A extensão vem do `filename` enviado pelo cliente (`os.path.splitext(arquivo.filename)[1]`).
- **Impacto:**
  - Upload de `.html`/`.svg`/`.js` servido sob o mesmo origin (`/static/...`) viabiliza **stored XSS**.
  - Inundação de disco (DoS) e consumo de armazenamento da hospedagem grátis.
- **Recomendação:** Validar tamanho máximo (ex.: 2–5 MB), verificar mime/assinatura real do arquivo (Pillow para imagens), usar apenas extensões permitidas (`.jpg`, `.png`, `.webp`), salvar sem extensão/via storage externo (S3/R2) com Content-Type fixo; adicionar `Content-Disposition: attachment` ou servir uploads de um host/CDN separado.

### 🔴 ALTO — Stored XSS via `innerHTML` com dados do usuário

- **Local:** `static/app.js:372-394` (produtos), `911-929` (clientes), `480-500` (vendas), entre outros
- **Descrição:** Nome/descrição/observações/telefone vindos da API são interpolados direto em `innerHTML` sem escape/`textContent`. Como não há autenticação, **qualquer visitante pode cadastrar um cliente/produto com payload `<img onerror=...>` executado para todos os demais visitantes**.
- **Impacto:** Sequestro de sessão futuro, roubo de dados exibidos, defacement, redirecionamentos maliciosos.
- **Recomendação:** Substituir interpolação por `textContent`/`createElement` ou usar biblioteca de escape (ex.: `escapeHtml()`); nunca injetar campos do usuário em `innerHTML`.

### 🟠 MÉDIO — CORS excessivamente permissivo

- **Local:** `main.py:49-55`
- **Descrição:** `allow_origins=["*"]` com `allow_credentials=True` e `allow_methods/headers=["*"]`.
- **Impacto:** A configuração é inválida para navegadores (que rejeitam `*` + credentials), mas sinaliza política frouxa; quando houver cookies/sessões, será vetor para ataques cross-origin.
- **Recomendação:** Restringir a origins reais (`https://calculadora-mei.onrender.com`) e remover `allow_credentials` enquanto não houver cookies.

### 🟠 MÉDIO — SSL do banco com verificação desabilitada

- **Local:** `database.py:39-43`
- **Descrição:** Ao usar `sslmode=require`, o código cria contexto SSL com `check_hostname = False` e `verify_mode = CERT_NONE`.
- **Impacto:** Permite MITM na conexão com o banco (senha/dados trafegando possivelmente para um impostor).
- **Recomendação:** Usar `sslmode=verify-full` (verificar hostname + CA) na connection string e remover o bloco de `CERT_NONE`.

### 🟠 MÉDIO — Endpoints de escrita sem rate limiting e webhook sem idempotência

- **Local:** `main.py:441-727`; `main.py:210-239`
- **Descrição:** Não há limitação de requisições. Um script pode criar milhares de clientes/vendas/despesas (poluição do banco, DoS barato) e o webhook pode ser enviado em duplicidade sem consequência controlada.
- **Recomendação:** Middleware de rate limit (ex.: `slowapi`) por IP/rota; idempotência no webhook por `payment_id` (chave única).

### 🟡 BAIXO — `GET /api/health` vaza metadados de negócio

- **Local:** `main.py:142-153`
- **Descrição:** Expõe quantidade de assinaturas ativas, tabela DAS e versão.
- **Impacto/Recomendação:** Baixo, mas evite expor contagens internas em endpoint público; mover para endpoint autenticado ou ocultar `assinaturas_ativas`.

### 🟡 BAIXO — Token padrão do Mercado Pago `"TEST-xxx"`

- **Local:** `main.py:20-21`
- **Descrição:** Se `MP_ACCESS_TOKEN`/`MP_PUBLIC_KEY` não estiverem definidos no ambiente, o app roda com token fictício e o checkout falha silenciosamente.
- **Recomendação:** Remover os fallbacks e falhar na inicialização se variáveis ausentes (missão: impedir produção com configuração quebrada).

### ✅ BOM — SQL Injection adequadamente mitigado

- **Local:** `database.py` (todas as queries)
- **Descrição:** Todas as consultas usam placeholders `$1…` do asyncpg — inclusive `LIKE`/`ILIKE` (`database.py:191,225,261`) e `customer_aniversario` (`database.py:287`). Não foi encontrada concatenação de entrada do usuário em SQL.
- **Manutenir:** Continuar com parametrização; nunca concatenar `f"{user}"` em SQL mesmo em refatorações futuras.

---

## 2. Achados LGPD

### 🔴 ALTO — Política de Privacidade declara dados incorretos (falsa sensação de segurança)

- **Local:** `templates/privacidade.html:34-40` (“**NAO coleta, armazena ou transmite dados pessoais**… processam-se exclusivamente no navegador”)
- **Descrição:** Afirmação **falsa**: o app armazena clientes (nome, telefone, e-mail, endereço, aniversário — art. 5º I LGPD), produtos, vendas, despesas e assinaturas em PostgreSQL (`database.py`), e envia nome/e-mail do comprador ao Mercado Pago (`main.py:174-179`).
- **Impacto:** Descumprimento de princípio da transparência (art. 6º VI); titular é induzido a erro e não exercerá seus direitos. Multa ANPD pode chegar a 2% do faturamento (arts. 52-53).
- **Recomendação:** Reescrever a página descrevendo verdadeiramente: dados coletados, finalidade, base legal, retenção, compartilhamento e direitos.

### 🔴 ALTO — Ausência de mecanismo de requerimentos do titular (LGPD arts. 9, 18)

- **Descrição:** Não há botão/página para **solicitar cópia (portabilidade/confirmação), correção, exclusão ou revogação de consentimento**. Os endpoints `DELETE /api/clientes` são internos, sem autenticação e sem chave do titular.
- **Recomendação:**
  1. Criar ferramenta acessível em `/privacidade` e no rodapé: **“Solicitar exclusão de dados”** e **“Exportar meus dados”** (formulário e-mail/CPF → verificação) mapeadas a endpoints autenticados e auditados.
  2. Atender em até 15 dias (art. 18 §2º, conforme alteração da Lei 14.460/2022 — art. 18 §6º recomenda prazos e plataformas).
  3. Registrar Log de tratamento (art. 37) e evidenciar cada pedido atendido.

### 🟠 MÉDIO — Política de Privacidade incompleta (faltam elementos obrigatórios)

- **Local:** `templates/privacidade.html`
- **Faltam / precisam de ajuste:**
  - **Finalidade** específica de cada dado (ex.: cobrança, CRM/vendas, cálculo).
  - **Base legal** (art. 7º: consentimento, execução de contrato, cumprimento de obrigação legal/tributária p/ DAS; legítimo interesse p/ melhorias).
  - **Compartilhamento:** Mercado Pago (contas a receber) e **SISGERSA (banco compartilhado)** — hoje a política só cita “Hosting” e “Google Fonts”.
  - **Retenção/período** de armazenamento e procedimento de eliminação.
  - **Direitos completos do titular** (arts. 18/19): confirmação, acesso, correção, anonimização, portabilidade, oposição, revogação.
  - **Encarregado (DPO)** nomeado e identificável (hoje apenas “Encarregado de Dados: Calculadora MEI”, sem contato específico).
  - Cookies: a seção 2 cita cookie essencial sem identificá-lo.
- **Recomendação:** Revisar com suporte jurídico e adotar modelo completo (base legal + tabela de dados + mapa de compartilhamento + prazos).

### 🟠 MÉDIO — Termos de Uso sem cláusulas de serviço pago

- **Local:** `templates/termos.html`
- **Descrição:** Não há menção ao **Plano PRO (R$ 9,90/mês)**, a cobrança automática recorrente via Mercado Pago, política de **cancelamento/reembolso**, ou **alteração de preços**. O item 8 fala em “alterações” genéricas; o 9 aponta só legislação brasileira sem foro.
- **Recomendação:** Adicionar seções: valores e planos, cobrança recorrente e cancelamento do plano (CDC arts. 49-51 + LGPD), política de reembolso, suspensão/encerramento de conta, foro (sugestão: comarca da sede do titular para consumidores — art. 6º inciso VIII e art. 101 CDC), e referência expressa à LGPD.

### 🟡 BAIXO — Menores / marketing

- **Descrição:** Serviço é direcionado a adultos (MEIs), mas a base de clientes pode conter terceiros (clientes do MEI). A política afirma corretamente o foco em maiores de 18 (item 6).
- **Recomendação:** Se houver intenção de marketing direto (aniversário, lembretes), deixar claro a atividade de tratamento de dados de terceiros (clientes do usuário) e a responsabilidade de cada ocupante.

---

## 3. Quadro de conformidade LGPD (checklist)

| Requisito (art.) | Status | Onde |
|---|---|---|
| Transparência / informação precisa (art. 6º VI, 9) | ❌ | Política afirma não coletar dados pessoais |
| Base legal definida (art. 7º) | ❌ | Não consta |
| Finalidade (art. 6º I) | ⚠️ | Parcial, genérica |
| Compartilhamento com operadores (Mercado Pago/SISGERSA) (arts. 6º VII, 9) | ❌ | Não citado |
| Direitos do titular (art. 18) | ❌ | Mencionado genericamente; sem mecanismo funcional |
| Botão exportação/exclusão (arts. 9, 18) | ❌ | Não existe |
| Encarregado/DPO identificável (art. 41) | ⚠️ | Cite «Encarregado de Dados» sem nome/contato |
| Segurança / medidas técnicas (arts. 46-49) | ⚠️ | HTTPS + parametrização OK; falhas de auth/upload comprometem |
| Registro de tratamento (art. 37) | ❌ | Não localizado |
| Menores (art. 14) | ✅ | Não direcionado a menores |
| ANPD indicada (art. 55-K ss.) | ✅ | Citada (item 9) |

---

## 4. Plano de ação prioritário (roadmap)

1. **(Urgente)** Rotacionar credencial do banco e remover fallback de `database.py`; adicionar `.gitignore`; rodar scanner de segredos.
2. **(Urgente)** Implementar autenticação + escopo por usuário em todas as rotas `/api/*`; `DELETE` sem auth deve ser bloqueado.
3. **(Urgente)** Validar `x-signature` e idempotência do webhook Mercado Pago.
4. **(Alta)** Validar uploads (tamanho, MIME, extensão) e servir de forma segura; sanitizar renderização no front-end (`textContent`).
5. **(Alta)** Reescrever Política de Privacidade (dados reais, finalidade, base legal, compartilhamento, retenção, direitos) e expandir Termos de Uso (Plano PRO, cobrança, cancelamento, reembolso, foro).
6. **(Média)** Criar fluxos “Exportar meus dados” e “Solicitar exclusão” (LGPD art. 18) com verificação do titular.
7. **(Média)** Corrigir CORS, SSL do banco (verify-full), rate limiting e health check.

---

*Relatório gerado por agente de Segurança e Conformidade (LGPD). Nenhum arquivo do projeto foi modificado nesta auditoria.*