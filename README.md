# Cúpula de Gestão Autônoma

Sistema multi-agente com 15+ agentes, Setor Jurídico (20 leis brasileiras), AI Gateway, meta-agentes e webhooks.

## Início Rápido

### Requisitos
- Python 3.12+
- Docker + Docker Compose (para stack completa)
- Redis (para desenvolvimento local)

### Rodar Local (desenvolvimento)

```bash
# 1. Clonar e instalar dependências
git clone <repo>
cd cupula-gestao
pip install -r requirements.txt

# 2. Iniciar Redis (via Docker)
docker run -d --name cupula-redis -p 6379:6379 redis:7-alpine

# 3. Iniciar a API
python -m cupula.api.main

# API disponível em http://localhost:8080
# Docs: http://localhost:8080/docs
```

### Rodar com Docker Compose (produção)

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API

# 2. Subir tudo
docker compose up -d

# Serviços:
#   API:     http://localhost:8080
#   n8n:     http://localhost:5678
#   Redis:   localhost:6379
```

## Endpoints da API

### Core
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/health` | Status geral do sistema |
| GET | `/api/v1/status` | Detalhes dos agentes |
| GET | `/api/v1/leaderboard` | Ranking de reputação |
| GET | `/api/v1/report` | Relatório completo |
| GET | `/api/v1/meta/analyze` | Análise dos meta-agentes |

### Decisões
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/decide` | Enviar decisão (ativa Cúpula + Legal) |
| POST | `/api/v1/legal/analyze` | Análise jurídica direta |
| GET | `/api/v1/legal/stats` | Estatísticas do setor jurídico |

### AI Capabilities
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/ai/capabilities` | Lista capabilities disponíveis |
| POST | `/api/v1/ai/code/generate` | Gerar código |
| POST | `/api/v1/ai/code/review` | Revisar código |
| POST | `/api/v1/ai/code/debug` | Debugar código |
| POST | `/api/v1/ai/image/generate` | Gerar imagem |
| POST | `/api/v1/ai/copy/create` | Criar copy |
| POST | `/api/v1/ai/brainstorm` | Brainstorm |
| POST | `/api/v1/ai/vision/screenshot` | Análise de screenshot |
| POST | `/api/v1/ai/vision/ocr` | OCR em imagem |
| POST | `/api/v1/ai/vision/compare` | Comparar 2 imagens |

### Webhooks (n8n / integrações externas)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/webhook` | Webhook genérico |
| POST | `/api/v1/webhook/decision` | Dispara decisão via webhook |
| POST | `/api/v1/webhook/legal` | Análise jurídica via webhook |
| POST | `/api/v1/webhook/n8n` | Integração n8n |
| POST | `/api/v1/webhook/status` | Status do worker |
| GET | `/api/v1/worker/stats` | Métricas do worker |

## Exemplos

### Decisão com análise legal automática
```bash
curl -X POST http://localhost:8080/api/v1/decide \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implantar chatbot com IA",
    "description": "Chatbot para atendimento coletando dados pessoais (LGPD)",
    "priority": 8,
    "auto_legal": true
  }'
```

### Webhook do n8n
```bash
curl -X POST http://localhost:8080/api/v1/webhook/n8n \
  -H "Content-Type: application/json" \
  -d '{
    "action": "trigger_decision",
    "title": "Expansão para novo estado",
    "description": "Abrir filial, envolve CLT e ICMS"
  }'
```

## Arquitetura

```
                    ┌──────────────┐
                    │   n8n        │
                    │  (workflows) │
                    └──────┬───────┘
                           │ webhook
                    ┌──────▼───────┐
                    │  FastAPI      │
                    │  (port 8080)  │
                    └──┬───┬───┬───┘
                       │   │   │
          ┌────────────┘   │   └────────────┐
          ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────────┐
   │  Cúpula   │    │  Legal    │    │  AI Gateway  │
   │ (4 agentes)│   │ (5 agentes)│   │ (3 caps)     │
   └──────────┘    └──────────┘    └──────────────┘
          │                │                │
          └────────┬───────┴────────────────┘
                   ▼
            ┌──────────┐
            │ EventBus  │
            │ (Redis)   │
            └──────────┘
                   ▲
            ┌──────┴──────┐
            │   Worker     │
            │ (autônomo)   │
            └─────────────┘
```

## Agentes

### Cúpula (decisões)
- **Sentinel** — segurança e compliance
- **Nexus** — viabilidade técnica
- **Vortex** — viabilidade de negócio
- **Apolo** — síntese holística

### Setor Jurídico (5 agentes, 20 leis)
- **Legislator** — interpretação de leis
- **Compliance** — verificação de conformidade
- **Jurisprudence** — análise de jurisprudência
- **Risk Legal** — avaliação de risco jurídico
- **Regulatory** — mudanças regulatórias

### Meta-Agentes
- **SelfImprover** — sugere melhorias no sistema
- **Auditor** — auditoria de comunicações
- **Optimizer** — otimização de performance
- **Analyst** — análise de padrões de decisão

### AI Gateway
- **Vision** — análise visual, OCR, screenshots
- **Code** — geração, revisão e debug de código
- **Creative** — imagens, copy, brainstorm

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `REDIS_URL` | `redis://localhost:6379` | URL do Redis |
| `API_HOST` | `0.0.0.0` | Host da API |
| `API_PORT` | `8080` | Porta da API |
| `OPENAI_API_KEY` | — | Chave OpenAI (AI Gateway) |
| `ANTHROPIC_API_KEY` | — | Chave Anthropic (AI Gateway) |
| `GOOGLE_API_KEY` | — | Chave Google (AI Gateway) |
| `ELEVENLABS_API_KEY` | — | Chave ElevenLabs (AI Gateway) |
