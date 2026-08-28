# DEV_OPS — Auditoria de Infraestrutura · Calculadora MEI

Data da auditoria: **2026-08-27** · Agente: DevOps
App: https://calculadora-mei.onrender.com · Service ID: `srv-da7rfd5g1s2s73f5jtk0`
Repo: https://github.com/marcusodontocotta-ui/calculadora-mei (monorepo, app em `projects/calculadora-mei/`)

---

## Resumo executivo

| Item | Status |
|---|---|
| Serviço | 🟢 **Live** (não suspenso), deploy atual saudável |
| Health check | 🟢 `/api/health` responde `healthy` · 1 assinatura ativa |
| Banco | 🟢 Conectividade OK (PostgreSQL 18.4) — mas **compartilhado** com SISGERSA |
| Segurança | 🔴 **C1 (crítico)** — credencial do banco hardcoded e commitada; API do Render sem `DATABASE_URL` |
| Backup | 🔴 Nenhuma estratégia existia → criado `BACKUP.md` + snapshot validado |
| Config | 🟡 `render.yaml` e `Dockerfile` desatualizados/inconsistentes com o serviço real |

**Veredito**: aplicação está no ar e saudável, porém com 1 risco crítico (segredo em repositório)
e 1 risco alto (banco compartilhado + sem backup). As ações recomendadas das seções 8 e 9 devem
ser priorizadas nesta ordem.

---

## 1. Status do serviço e último deploy (Render API)

- **Serviço**: `calculadora-mei` · type `web_service` · runtime Python (buildpacks)
- **Plano**: `starter` (0.5 CPU / 512 MB) · 1 instância · região `oregon`
- **Criado**: 2026-08-27T04:06Z · **Atualizado**: 2026-08-28T01:24Z
- **autoDeploy**: yes (trigger commit · branch `main`) · rootDir vazio
- CORS/IP allow list: `0.0.0.0/0` · porta aberta TCP 10000

Deploys recentes (5):

| Deploy | Commit | Status | Trigger |
|---|---|---|---|
| `dep-da8e665…` 01:23Z | `dc4b27e9` fix webhook assinatura | 🟢 **live** | api |
| `dep-da8doej…` 00:54Z | `e378a6a7` MP checkout preference | ⚪ deactivated | api |
| `dep-da8dc0b…` 00:27Z | `3db678d0` asyncpg DSN scheme | ⚪ deactivated | api |
| `dep-da7risl…` 04:13Z | `3db678d0` | ⚪ deactivated | api |
| `dep-da7rgn8…` 04:09Z | `e8e23e94` buildpacks + SSL | 🔴 **update_failed** | manual |

Observações:
- Deploy atual (`dc4b27e9`) está `live` desde 01:24Z. O commit bate com o HEAD local.
- Houve 1 deploy com **build falho** (`srv` → update_failed) em 27/08, já superado.
- Todos os 5 últimos deploys têm trigger **`api`** — confirmar na prática se o auto-deploy por push no
  GitHub está disparando; se o fluxo do time é via API/CLI (`render deploy`), manter assim e documentar.

## 2. Health check do app

```
GET https://calculadora-mei.onrender.com/api/health
→ status: healthy · version 1.0.0 · assinaturas_ativas: 1 · teto_anual 81.000
```

O endpoint consulta o banco (`contar_assinaturas_ativas`) — ou seja, mede app **e** banco.
**Mas** o Render NÃO está usando esse endpoint: `healthCheckPath: ""` no serviço → o Render usa
TCP probe padrão + rota `/`. Melhoria na seção 8 (I1).

## 3. Revisão — Dockerfile, render.yaml, requirements.txt

### `Dockerfile`
- ❌ **Não é usado no Render**: o serviço roda em **buildpacks Python** (runtime `python`) com
  `buildCommand`/`startCommand` custom. O Dockerfile é código morto e confunde (dois caminhos de deploy).
- Se um dia for usado: roda como **root**, `COPY . .` copia `__pycache__`/testes, `EXPOSE 8000`
  diverge do `$PORT` (10000) do Render, e não há `HEALTHCHECK`.

### `render.yaml`
- ❌ **Desatualizado**: `plan: free`, mas o serviço real está em **starter**. Um `render blueprint
  apply` rebaixaria o plano.
- ❌ **Sintaxe de caminho**: `buildCommand: pip install -r requirements.txt` **sem** `rootDir`.
  O serviço real usa `cd projects/calculadora-mei && pip install ...`. Aplicar o blueprint direto
  quebraria o build.
- ❌ `DATABASE_URL` com `fromDatabase: sisgersa-db` — o banco não é declarado neste repo (é do
  SISGERSA/cupula). Outro blueprint não resolve. Além disso, o serviço **não tem** essa env var hoje.
- 🟡 Falta `healthCheckPath`; região não pinada (live é oregon).

### `requirements.txt`
- ✅ Dependências corretas para o app (FastAPI, uvicorn, pydantic, asyncpg, python-multipart, httpx).
- ❌ Versões soltas `>=` → builds não reproduzíveis. Pinversionar (ex.: `==`) ou usar `~=` + lock.

## 4. Banco de dados e segurança

### C1 — CRÍTICO: credencial do banco commitada no código (e no GitHub)
- `projects/calculadora-mei/database.py:13` **hardcoda** a connection string do banco `sisgersa`
  (usuário app `sisgersa_app`). Confirmada idêntica na branch `main` do GitHub.
- A API do Render retorna **apenas 2 env vars** (`MP_PUBLIC_KEY`, `MP_ACCESS_TOKEN`) —
  **`DATABASE_URL` NÃO está configurada**. Logo o app em produção depende da credencial vazada.
- Impacto: quem tiver acesso ao repo tem acesso de leitura/escrita a **todo o banco compartilhado,
  incluindo dados do SISGERSA** (pacientes, prontuários, etc.).
- Ação: configurar `DATABASE_URL` como secret no Render, remover o fallback hardcoded e
  **rotacionar a senha** (em coordenação com o time do SISGERSA, pois é a mesma instância).

### C2 — ALTO: dependência do app no banco de produção do SISGERSA
- Mesma instância (`dpg-d9hqikr7uimc73dt3e0g-a.oregon-postgres.render.com`, PG 18.4) com ~70 tabelas
  do SISGERSA. Isolamento só por prefixo `mei_*`.
- Riscos: blast radius de qualquer erro da Calculadora atinge o SISGERSA e vice-versa; sem backup
  dedicado; `sisgersa_app` é usuário de aplicação com amplos privilégios.
- Ação de médio prazo: **criar um Postgres dedicado no Render** (Starter, com backups automáticos
  diários) e migrar as 5 tabelas `mei_*` (dados hoje: 4 assinaturas, 1 cliente).

### C3 — MÉDIO: verificação SSL desabilitada
- `database.py:39-43`: `check_hostname=False` e `CERT_NONE`. Adotar `sslmode=require` com
  verificação de certificado (Render expõe CA) — evita MITM e é pré-requisito de boas práticas.

### C4 — MÉDIO: webhook do Mercado Pago sem validação de assinatura
- `POST /api/webhook/mercadopago` (main.py:210) não valida o header `x-signature`/`data.id`.
  Qualquer POST com um `payment_id` conhecido ativa a assinatura. Adicionar verificação.

### C5 — BAIXO
- Upload de fotos salvo em disco local do container → **ephemeral** (some a cada redeploy).
- CORS aberto `*` com `allow_credentials=True` (inválido por spec; restringir).
- Chamadas `httpx` ao Mercado Pago sem `timeout` → risco de request pendurada.
- Índices simples; sem logging estruturado/agregação de erros (sem Sentry/Logtail).

## 5. Backup / estratégia de dados

- Nenhum script de backup existia (busca por `pg_dump|backup|restore` e nos scripts do repo).
- **Snapshot validado nesta auditoria**: `mei_backup_20260827_223630.dump` (formato custom, 12.630 B,
  SHA256 `B7A8EAE9…EF34`) com as 5 tabelas `mei_*` — integridade confirmada via `pg_restore --list`.
- **Roteiro completo de backup mensal criado**: ver **[BACKUP.md](BACKUP.md)** (procedimento manual via
  Docker `pg_dump 18`, automação com GitHub Actions mensal, restore/teste, retenção, checklist).

## 6. Logs

- A API pública do Render **não expõe logs** (nem de deploy, nem em runtime). Acesso disponível:
  Dashboard → serviço → **Logs** (stream) e **Events**, ou SSH (`sshAddress: srv-…@ssh.oregon.render.com`).
- Histórico: nenhum erro visto nos deploys recentes; o único `update_failed` foi build (27/08), sem
  impacto após os fixes de buildpack/DSN.
- Recomendação: adicionar **log drain** (Logtail/Papertrail/Sentry) para não depender só do console.

## 7. Resumo de problemas encontrados

| # | Severidade | Problema |
|---|---|---|
| C1 | 🔴 Crítico | Credencial do banco hardcoded + commitada; sem `DATABASE_URL` no Render |
| C2 | 🟠 Alto | Banco de produção compartilhado com SISGERSA; sem isolamento/backup dedicado |
| C3 | 🟠 Médio | SSL verification desabilitada na conexão do banco |
| C4 | 🟠 Médio | Webhook MP sem validação de assinatura |
| C5 | 🟡 Baixo | Uploads em disco efêmero; CORS aberto; httpx sem timeout; sem logs agregados |
| C6 | 🟡 Baixo | `render.yaml` obsoleto (free vs starter, sem rootDir, fromDatabase inválido) |
| C7 | 🟡 Baixo | `Dockerfile` não usado no Render (conflito de caminhos) |
| C8 | 🟡 Baixo | `requirements.txt` com versões soltas (build não reproduzível) |
| C9 | 🟡 Baixo | `healthCheckPath` do Render não configurado |

## 8. Melhorias recomendadas (com implementação)

### I1 — Health check HTTP no Render (quick win)
Configurar `healthCheckPath: /api/health`. O Render então: bane instâncias que falham por 15 s
(stack traffic), reinicia após 60 s de falha, e **cancela deploy** que não fique saudável em 15 min.
- Dashboard: Web Service → Settings → Health Checks → path `/api/health`.
- API:
  ```
  PATCH https://api.render.com/v1/services/srv-da7rfd5g1s2s73f5jtk0
  { "serviceDetails": { "healthCheckPath": "/api/health" } }
  ```
- Blueprint: adicionar `healthCheckPath: /api/health` em `render.yaml`.

### I2 — Remover segredo do código + configurar `DATABASE_URL` (emergência)
1. No Render, criar env var `DATABASE_URL` (String; valor = connection string atual) e marcar como secret.
2. Em `database.py`, remover o fallback hardcoded: usar só `os.environ["DATABASE_URL"]` (falhar cedo
   se ausente), mantendo um mecanismo de `.env` apenas para dev local.
3. **Rotacionar a senha** do usuário da app (coordenar com SISGERSA; atualizar Render, GitHub secret
   `DATABASE_URL` de backup, e o time).

### I3 — Banco dedicado para a Calculadora MEI (médio prazo)
1. Criar Postgres Starter no Render (região oregon) — já inclui **backups automáticos diários**.
2. Migrar: `pg_dump -t "mei_*"` do banco atual → `pg_restore` no novo banco (ver BACKUP.md §5).
3. Apontar `DATABASE_URL` do serviço para o novo banco. Zero downtime (dump+restore das 5 tabelas é instantâneo).
4. Remover privilege do usuário `sisgersa_app` após migração (com o time SISGERSA).

### I4 — Automação de backup (ver BACKUP.md §4)
GitHub Actions mensal com `pg_dump 18` + validação + upload S3/R2 + notificação. Secrets:
`DATABASE_URL`, e opcionais AWS/Telegram.

### I5 — Health/rota de monitoramento externo
Adicionar monitor externo (UptimeRobot/UptimeKuma, `GET /api/health`, alerta Telegram/e-mail)
para detectar lentidão/indisponibilidade fora dos deploys.

### I6 — Hardening de código (baixo esforço)
- SSL do banco: `sslmode=require` + verificação de CA.
- Webhook MP: validar `x-signature` (HMAC com `X-Id`/`X-Timestamp`) ou pelo menos `Authorization`.
- `httpx` com `timeout=httpx.Timeout(10.0)` nas chamadas ao Mercado Pago.
- CORS restrito aos domínios reais (o frontend é servido pelo próprio app — pode remover `*`).
- Uploads → armazenamento externo (R2/S3) e validação de tipo/tamanho.
- Logging estruturado + Sentry (ou Logtail via log drain).

### I7 — Pipeline/config
- Atualizar `render.yaml`: `plan: starter`, `rootDir: projects/calculadora-mei` (e então o
  `buildCommand` vira só `pip install -r requirements.txt`), `healthCheckPath: /api/health`,
  **remover** `fromDatabase`/`sisgersa-db` e usar env var manual.
- **Escolher um único caminho de deploy**: manter buildpacks e apagar o `Dockerfile` (ou migrar para
  Docker e alinhar `EXPOSE`/`$PORT`/usuário não-root). Recomendação: ficar com buildpacks (já funciona).
- Pinversionar `requirements.txt` (ex.: `fastapi==0.115.*` etc.) e rodar `pip-audit` em CI.

### I8 — Escala (não urgente)
- **Autoscaling do Render só existe em workspace Pro** — na configuração atual (Starter) use **escala
  manual** (2ª instância) se a carga crescer (billing prorrateado; nota: escala manual deixa de valer
  se houver persistent disk).
- Para o volume atual (estatística + 1–4 assinaturas) 1 instância Starter é o ideal custo/benefício.
- Ative `service previews` (PR) e/ou proteção de deploy se o time quiser testar antes de merge.

## 9. Plano de ação priorizado

1. **(hoje) I2** — `DATABASE_URL` como secret no Render + remover credencial hardcoded + agendar rotação.
2. **(hoje) I1/C9** — health check `/api/health` no Render.
3. **(esta semana) I4** — rodar o backup mensal automatizado (BACKUP.md) usando o snapshot atual como linha de base.
4. **(mês) I3** — criar Postgres dedicado e migrar `mei_*` (elimina C2 e ganha backup diário do Render).
5. **(mês) I6 + I7** — hardening C3/C4/C5 e alinhamento de `render.yaml`/`Dockerfile`/`requirements`.
6. **(contínuo) I5** — monitoramento externo.

---

### Anexo — artefatos produzidos na auditoria
- `BACKUP.md` — roteiro mensal de backup (pg_dump 18, automação GH Actions, restore, retenção).
- Snapshot validado: `mei_backup_20260827_223630.dump` (12.630 B; SHA256 `B7A8EAE99A17ADC4660527F57E5CAFEAC620285D7467FC88881787C4A784EF34`).
- Evidências de API utilizadas: `GET /v1/services/{id}`, `GET /v1/services/{id}/deploys`,
  `GET /v1/services/{id}/env-vars`, `GET /api/health`, conexão asyncpg (PG 18.4), `pg_dump`/`pg_restore` via Docker.