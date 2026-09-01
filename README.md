# Cúpula de Gestão Autônoma

Sistema multi-agente com Setor Jurídico, AI Gateway e meta-agentes.

> Este repositório contém também `projects/calculadora-mei/` (aplicação separada da Calculadora MEI).
> Este README descreve a plataforma **Cúpula** — o código em `cupula/`, `Dockerfile`, `Dockerfile.worker`, `docker-compose.yml` e `pyproject.toml`.

## Arquitetura

- **API** (`cupula/api/`) — FastAPI, expõe as rotas `/api/v1/*` (decisões, jurídico, AI, webhooks).
- **Worker** (`cupula/worker/`) — processo dedicado que consome Redis Streams (event-driven), executa cron de saúde/métricas e meta-análises.
- **Orquestrador / Core** (`cupula/core/`) — barramento, métricas, reputação, circuit breaker, batch, conferidor, memória.
- **Setor Jurídico** (`cupula/legal_gateway/`) — agentes jurídicos (legislador, compliance, jurisprudência, risco, regulatório).
- **AI Gateway** (`cupula/ai_gateway/`) — provedores OpenAI / Anthropic / Google para código, visão e criatividade.
- **Agentes** (`cupula/agents/`) — sentinel, nexus, vortex, apolo + meta-agentes (self-improver, auditor, otimizador, analista).

## Autenticação (obrigatória)

Todas as rotas `/api/v1/*` exigem o cabeçalho **`X-API-Key`** com o valor da env var **`CUPULA_API_KEY`**.

- O endpoint `/api/v1/health` é **público** (isento de auth) para health checks, retornando apenas dados não sensíveis.
- Sem `CUPULA_API_KEY` configurada no servidor, as rotas protegidas respondem **503** (fail-closed).
- Nunca commitar a chave real — use `.env` (ignorado pelo git).

### Como ativar

```bash
# gera uma chave forte
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Linux/macOS
export CUPULA_API_KEY='<chave-gerada>'

# Windows PowerShell
$env:CUPULA_API_KEY='<chave-gerada>'

# exemplo de chamada
curl -H "X-API-Key: $CUPULA_API_KEY" http://localhost:8080/api/v1/status
curl http://localhost:8080/api/v1/health   # público
```

## Executar localmente (sem Docker)

```bash
pip install -r requirements.txt
export CUPULA_API_KEY='<chave-gerada>'
export REDIS_URL='redis://localhost:6379/0'   # ajuste conforme seu Redis
python -m cupula.api.main
python -m cupula.worker.main                  # em outro terminal
```

## Executar com Docker Compose

```bash
cp .env.example .env   # preencha CUPULA_API_KEY e REDIS_PASSWORD
docker compose build
docker compose up -d
```

O compose inicia `redis` (com senha, porta publicada apenas em 127.0.0.1), `n8n`, `cupula-api` e `cupula-worker` (2 réplicas, cada uma com consumidor Redis Streams único).

## Modelo de consumo do Worker

A API **não** roda worker embutido. O consumo dos Redis Streams é feito **exclusivamente** pelo serviço `cupula-worker` (compose). Cada réplica usa um consumidor único (`REDIS_CONSUMER_NAME`) no mesmo grupo (`REDIS_CONSUMER_GROUP`) — consomem em paralelo sem duplicar mensagens.

## Variáveis de ambiente

Veja `.env.example` para a lista completa. Destaques:

- `CUPULA_API_KEY` — **obrigatória** para a API (P1a).
- `REDIS_PASSWORD` — senha do Redis / `REDIS_URL` autenticada (P2).
- `REDIS_CONSUMER_GROUP` / `REDIS_CONSUMER_NAME` — identidade do worker (P1c).
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` — opcionais, para o AI Gateway.

## Testes

```bash
python -m pytest
```
