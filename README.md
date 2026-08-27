# Calculadora MEI - DAS Simplificado

App web para Microempreendedores Individuais calcularem o DAS mensal, simularem cenarios de faturamento e receberem alertas de vencimento.

## Funcionalidades

- **Calculo do DAS**: Calcula o valor fixo mensal (INSS + ICMS/ISS)
- **Simulador de Cenarios**: Compara diferentes niveis de faturamento
- **Alertas de Vencimento**: Avisa antes do dia 20 de cada mes
- **Dashboard**: Visao geral com indicadores principais
- **Tabela DAS 2025**: Valores atualizados conforme Lei 14.848/2024

## Como Executar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python main.py

# Acessar no navegador
http://localhost:8081
```

## API Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/health` | GET | Health check |
| `/api/calcular-das` | POST | Calcula DAS mensal |
| `/api/simular` | POST | Simula cenarios |
| `/api/alertas` | GET | Alertas de vencimento |
| `/api/tabela-das` | GET | Tabela completa |
| `/api/dashboard` | Dados agregados |

## Estrutura

```
calculadora-mei/
 main.py           # Backend FastAPI
  calculadora.py    # Logica de calculos
  templates/
    index.html      # Frontend SPA
  static/
    style.css       # Estilos
    app.js          # JavaScript
  requirements.txt
```

## Tecnologias

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: HTML5 + CSS3 + JavaScript vanilla
- **Legislacao**: Lei 12.846/2013 + Lei 14.848/2024

## Licenca

Desenvolvido pela Cupula de Gestao Autonoma - ProjetoDefault
