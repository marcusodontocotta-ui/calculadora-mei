"""
Analise de Mercado - Submete os 5 melhores candidatos a Cupula de Gestao
para decisao coletiva com analise legal incluida.
"""
import asyncio
import httpx
import json
import sys
import io
import os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_URL = "http://localhost:8080"

CANDIDATES = [
    {
        "title": "Scanner de Notas Fiscais (Foto-Fatura -> Planilha)",
        "description": (
            "App mobile que fotografa notas fiscais/faturas e usa OCR + IA para extrair "
            "dados (fornecedor, valor, data, categoria). Exporta para Excel/Google Sheets. "
            "Ideal para pequenos lojistas, MEIs e pessoas que querem controle financeiro pessoal. "
            "O mercado brasileiro tem 22 milhoes de MEIs e alta demanda por simplificacao fiscal."
        ),
        "context": {
            "mercado": "22M+ MEIs no Brasil, faturamento estimado do mercado de apps financeiros: R$ 2.8B/ano (Statista)",
            "concorrencia": "Foto-fatura tem versao gratuita limitada; Scanner Pro e pago; nenhuma solucao dominante para MEIs",
            "modelo_receita": "Freemium: 10 fotos/mes gratis, R$ 19.90/mes para ilimitado + exportacao",
            "complexidade": "Baixa - OCR (Tesseract/cloud), backend simples, sem infra complexa",
            "tempo_desenvolvimento": "4-6 semanas (MVP funcional)",
            "tecnologias": "React Native ou Flutter, Python/Node.js backend, OCR (Tesseract ou API cloud), SQLite/local DB",
            "diferenciais": "Foco em MEIs brasileiros, categorizacao automatica por CFOP, integracao com planilhas",
            "risco": "Baixo - mercado validado, tecnologia madura, demanda real"
        },
        "constraints": [
            "Deve funcionar offline (ocr local)",
            "Compliance com LGPD (dados financeiros)",
            "Suporte a NF-e, NFC-e e notas manuais",
            "Exportacao para Excel e Google Sheets"
        ],
        "priority": 9
    },
    {
        "title": "Calculadora de MEI com Alertas",
        "description": (
            "App/web que calcula automaticamente impostos do MEI (DAS), prazos de pagamento, "
            "lucro real vs presumido, e envia alertas antes dos vencimentos. Inclui dashboard "
            "simples de faturamento mensal. Pode ser estendido para emitir NF-e."
        ),
        "context": {
            "mercado": "22M de MEIs, muitos sem assessoria contabil, pagam multas por atraso",
            "concorrencia": "Sebrae tem simulador web; apps existentes sao pagos ou complexos",
            "modelo_receita": "R$ 9.90/mes ou R$ 89.90/ano",
            "complexidade": "Muito baixa - calculos matematicos + notificacoes push",
            "tempo_desenvolvimento": "2-3 semanas (MVP)",
            "tecnologias": "Flutter/React Native, backend serverless (Supabase/Firebase)",
            "diferenciais": "Alertas proativos, simulacao de cenarios, linguagem simples",
            "risco": "Muito baixo - calculos baseados em legislacao publica"
        },
        "constraints": [
            "Calculos devem ser precisos conforme legislacao vigente",
            "Notificacoes push confiaveis",
            "Interface extremamente simples (MEIs nao sao tech-savvy)"
        ],
        "priority": 8
    },
    {
        "title": "Micro-journaling para Ansiedade",
        "description": (
            "App de journaling estruturado com prompts guiados de 2 minutos. "
            "Mood tracking diario, padroes identificados por IA, lembretes suaves. "
            "Mercado de saude mental cresce 20% ao ano. Semanalmente gera insights."
        ),
        "context": {
            "mercado": "Mercado global de apps de saude mental: $6.2B em 2025, CAGR 15.9%",
            "concorrencia": "Daylio e popular mas generico; Finch e para habitos; nenhum foca em ansiedade com prompts",
            "modelo_receita": "Freemium: 3 prompts/semana gratis, R$ 14.90/mes para ilimitado",
            "complexidade": "Baixa - prompts estaticos + mood tracker + notificacoes",
            "tempo_desenvolvimento": "3-4 semanas",
            "tecnologias": "Flutter, Supabase, IA para insights (OpenAI API)",
            "diferenciais": "Prompts baseados em TCC, modo offline, sem gamificacao excessiva",
            "risco": "Medio - mercado competitivo, retencao pode ser desafiadora"
        },
        "constraints": [
            "Prompts devem ser validados por profissionais de saude mental",
            "Dados sensiveis - LGPD rigorosa",
            "Nao pode substituir terapia - disclaimer obrigatorio"
        ],
        "priority": 7
    },
    {
        "title": "Rastreador de Ruido do Bairro",
        "description": (
            "App crowdsourced que permite moradores documentarem niveis de ruido com "
            "medicao do microfone + geolocalizacao. Gera relatorios para condominios "
            "e prefeituras. Zero concorrencia, mercado inexplorado."
        ),
        "context": {
            "mercado": "Reclamacoes por ruido crescem 30% ao ano em SP; 40% dos brasileiros reportam problemas",
            "concorrencia": "Zero apps especificos no Brasil; SoundPrint existe nos EUA mas nao aqui",
            "modelo_receita": "Freemium + dados agregados para imobiliarias/prefeituras (B2B)",
            "complexidade": "Baixa - microfone + GPS + backend simples",
            "tempo_desenvolvimento": "3-5 semanas",
            "tecnologias": "Flutter, backend Python, SQLite, API de mapas",
            "diferenciais": "Crowdsourced, relatorios PDF, dados para politicas publicas",
            "risco": "Medio - adocao depende de massa critica de usuarios"
        },
        "constraints": [
            "Precisa de permissao de microfone",
            "Medicao calibrada (varia por dispositivo)",
            "LGPD - dados de localizacao sao sensiveis"
        ],
        "priority": 6
    },
    {
        "title": "Planejador de Refeicoes com Restricoes Alimentares",
        "description": (
            "App que monta cardapios semanais considerando restricoes (gluten, lactose, "
            "vegetariano, etc.), gera lista de compras e controle orcamento. "
            "Mercado de bem-estar cresce 12% ao ano no Brasil."
        ),
        "context": {
            "mercado": "5% da populacao brasileira tem intolerancia a lactose; 1% tem doença celíaca",
            "concorrencia": "Paprika e Mealime existem mas sao ingles; sem foco brasileiro",
            "modelo_receita": "R$ 12.90/mes ou R$ 99.90/ano",
            "complexidade": "Media-baixa - banco de receitas + logica de filtragem + UI",
            "tempo_desenvolvimento": "4-6 semanas",
            "tecnologias": "Flutter, Node.js/Python, SQLite, API de nutricao",
            "diferenciais": "Receitas brasileiras, considera orcamento, lista de compras inteligente",
            "risco": "Baixo - demanda crescente, nicho claro"
        },
        "constraints": [
            "Receitas devem ser nutricionalmente balanceadas",
            "Database de valores nutricionais para calculos",
            "Interface acessivel para idosos"
        ],
        "priority": 7
    }
]


async def submit_decision(client: httpx.AsyncClient, candidate: dict) -> dict:
    """Envia candidato para analise do sistema Cupula."""
    payload = {
        "title": candidate["title"],
        "description": candidate["description"],
        "context": candidate["context"],
        "constraints": candidate["constraints"],
        "priority": candidate["priority"],
        "auto_legal": True
    }
    try:
        resp = await client.post(f"{API_URL}/api/v1/decide", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e), "title": candidate["title"]}


async def main():
    print("=" * 70)
    print("  CUPULA DE GESTAO - ANALISE DE MERCADO: APPS DE BAIXA COMPLEXIDADE")
    print("=" * 70)
    print(f"\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("Agentes registrados: verificando...\n")

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{API_URL}/api/v1/health", timeout=10)
            h = health.json()
            print(f"  Status: {h.get('status', 'unknown')}")
            print(f"  Agentes: {h.get('agents_registered', 0)}")
            print(f"  Lei DB: {h.get('legal_db_laws', 0)} leis")
            print(f"  Analises legais: {h.get('legal_analyses', 0)}")
            print()
        except Exception as e:
            print(f"  API offline: {e}")
            print("  Execute: python -m cupula.api.main")
            return

        results = []
        for i, candidate in enumerate(CANDIDATES, 1):
            print()
            print("-" * 70)
            print(f"  CANDIDATO {i}/{len(CANDIDATES)}: {candidate['title']}")
            print("-" * 70)
            print(f"  Complexidade: {candidate['context']['complexidade']}")
            print(f"  Tempo MVP: {candidate['context']['tempo_desenvolvimento']}")
            print(f"  Receita: {candidate['context']['modelo_receita']}")
            print(f"  Risco: {candidate['context']['risco']}")
            print("\n  Submetendo a Cupula...")

            result = await submit_decision(client, candidate)
            results.append(result)

            if "error" in result:
                print(f"  ERRO: {result['error']}")
                continue

            verdict = result.get("verdict", "N/A")
            confidence = result.get("confidence", 0)
            agent_count = result.get("responses_count", 0)
            risks = result.get("risks", [])
            recs = result.get("recommendations", [])
            legal = result.get("legal_analysis")

            print()
            print("  +----------------------------------------------------------+")
            print(f"  |  VEREDICTO: {verdict.upper():<47}|")
            print(f"  |  Confianca: {confidence:.1%}  |  Agentes: {agent_count:<27}|")
            print("  +----------------------------------------------------------+")

            if risks:
                print("\n  Riscos identificados:")
                for r in risks[:5]:
                    print(f"     * {r}")

            if recs:
                print("\n  Recomendacoes:")
                for r in recs[:5]:
                    print(f"     * {r}")

            if legal:
                parecer = legal.get("parecer", legal.get("verdict", "N/A"))
                conf_legal = legal.get("confianca", legal.get("confidence", 0))
                print(f"\n  Analise Legal: {parecer} (confianca: {conf_legal:.1%})")
                dominios = legal.get("dominios_afetados", [])
                if dominios:
                    print(f"     Dominios: {', '.join(dominios)}")

            agent_responses = result.get("agent_responses", [])
            if agent_responses:
                print("\n  Respostas dos Agentes:")
                for ar in agent_responses[:4]:
                    agent = ar.get("agent", "?")
                    resp_verdict = ar.get("verdict", "?")
                    resp_conf = ar.get("confidence", 0)
                    rationale = ar.get("rationale", "")[:80]
                    print(f"     [{agent}] {resp_verdict} ({resp_conf:.0%}) - {rationale}...")

        print()
        print("=" * 70)
        print("  RANKING FINAL - CANDIDATOS ANALISADOS")
        print("=" * 70)
        print()

        ranked = []
        for r, c in zip(results, CANDIDATES):
            if "error" in r:
                score = 0
            else:
                score = r.get("confidence", 0)
                cx = c["context"].get("complexidade", "").lower()
                if "muito baixa" in cx:
                    score += 0.05
                elif "baixa" in cx:
                    score += 0.03
            ranked.append((score, c["title"], r))

        ranked.sort(reverse=True)

        medals = ["1st", "2nd", "3rd", "4th", "5th"]
        for i, (score, title, r) in enumerate(ranked):
            medal = medals[i] if i < len(medals) else f"{i+1}th"
            verdict = r.get("verdict", "N/A") if "error" not in r else "ERRO"
            confidence = r.get("confidence", 0) if "error" not in r else 0
            print(f"  {medal} - {title}")
            print(f"       Score: {score:.3f} | Veredicto: {verdict} | Confianca: {confidence:.1%}")
            print()

        report = {
            "timestamp": datetime.now().isoformat(),
            "candidates": CANDIDATES,
            "results": results,
            "ranking": [{"score": s, "title": t} for s, t, _ in ranked]
        }
        report_path = "reports/market_analysis.json"
        try:
            os.makedirs("reports", exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            print(f"  Relatorio salvo em: {report_path}")
        except Exception as e:
            print(f"  Erro ao salvar relatorio: {e}")

        print()
        print("=" * 70)
        print("  ANALISE COMPLETA")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
