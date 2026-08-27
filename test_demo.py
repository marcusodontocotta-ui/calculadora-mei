import asyncio
import json
from cupula.app import CupulaApp


async def test():
    print("Creating app...", flush=True)
    app = CupulaApp()

    print("Starting...", flush=True)
    await app.start()
    print("Start OK", flush=True)

    print("Registering cupula agents...", flush=True)
    from cupula.agents.builtin.sentinel.agent import SentinelAgent
    from cupula.agents.builtin.nexus.agent import NexusAgent
    from cupula.agents.builtin.vortex.agent import VortexAgent
    from cupula.agents.builtin.apolo.agent import ApoloAgent

    app.orchestrator.register_agent("sentinel", SentinelAgent(), role="sentinel")
    app.orchestrator.register_agent("nexus", NexusAgent(), role="nexus")
    app.orchestrator.register_agent("vortex", VortexAgent(), role="vortex")
    app.orchestrator.register_agent("apolo", ApoloAgent(), role="apolo")
    print(f"Cupula agents registered: {len(app.orchestrator._agents)}", flush=True)

    print("\n--- DECISION 1: Sistema de clientes com IA ---", flush=True)
    result1 = await app.process_decision(
        title="Sistema de clientes com IA",
        description="Criar sistema que usa IA para analisar comportamento de clientes, "
                    "coletando dados de navegacao e compras para personalizacao.",
        context={"stack": ["Python", "Docker", "OpenAI"], "dados_sensiveis": True},
        constraints=["LGPD compliance", "Sandbox isolado"],
        priority=8,
    )
    print(f"  Veredito: {result1.get('verdict', 'N/A')}", flush=True)
    print(f"  Confianca: {result1.get('confidence', 'N/A')}", flush=True)
    print(f"  Agentes consultados: {result1.get('responses_count', 0)}", flush=True)

    print("\n--- LEGAL ANALYSIS 1: Sistema de dados de clientes ---", flush=True)
    legal1 = await app.legal_analysis(
        titulo="Sistema de analise de comportamento de clientes",
        descricao="Plataforma que coleta dados de navegacao, compras e "
                  "comportamento de usuarios para personalizacao de experiencia. "
                  "Usa inteligencia artificial para criar perfis de consumo.",
        dominios=["dados_pessoais", "consumidor", "digital"],
        acao_proposta="Criar sistema de profiling com IA",
        dados_envolvidos=["nome", "email", "historico de compras", "navegacao"],
    )
    opinion1 = legal1.get("opinion", {})
    print(f"  Veredito: {opinion1.get('veredito', 'N/A')}", flush=True)
    print(f"  Risco: {opinion1.get('risco', 'N/A')}", flush=True)
    print(f"  Leis aplicaveis: {len(opinion1.get('leis_aplicaveis', []))}", flush=True)
    for lei in opinion1.get("leis_aplicaveis", [])[:3]:
        print(f"    -> Lei {lei['lei']} ({lei['orgao']})", flush=True)
        print(f"       {lei['titulo']}", flush=True)

    print("\n--- LEGAL ANALYSIS 2: Exportacao software Europa ---", flush=True)
    legal2 = await app.legal_analysis(
        titulo="Exportacao de software para mercado europeu",
        descricao="Empresa brasileira quer vender software SaaS para clientes "
                  "na Uniao Europeia. Sistema coleta dados de usuarios europeus.",
        dominios=["dados_pessoais", "empresarial", "tributario", "digital"],
        acao_proposta="Expandir operacoes para Europa com coleta de dados GDPR",
        dados_envolvidos=["dados_pessoais_europeus", "dados_fiscais"],
    )
    opinion2 = legal2.get("opinion", {})
    print(f"  Veredito: {opinion2.get('veredito', 'N/A')}", flush=True)
    print(f"  Risco: {opinion2.get('risco', 'N/A')}", flush=True)
    for lei in opinion2.get("leis_aplicaveis", [])[:3]:
        print(f"    -> Lei {lei['lei']}: {lei['titulo']}", flush=True)

    print("\n--- GENERATING REPORT ---", flush=True)
    report = await app.generate_report()
    print(f"  Report #{report['report_id']}", flush=True)
    print(f"  Legal analyses: {report['legal_department']['total_analyses']}", flush=True)
    print(f"  Domains: {report['legal_department']['domains']}", flush=True)

    print("\n--- STOPPING ---", flush=True)
    await app.stop()
    print("All done!", flush=True)


if __name__ == "__main__":
    asyncio.run(test())
