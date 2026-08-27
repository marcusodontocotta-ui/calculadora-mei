import asyncio
import json


async def test_full():
    from cupula.app import CupulaApp
    from cupula.agents.builtin.sentinel.agent import SentinelAgent
    from cupula.agents.builtin.nexus.agent import NexusAgent
    from cupula.agents.builtin.vortex.agent import VortexAgent
    from cupula.agents.builtin.apolo.agent import ApoloAgent

    app = CupulaApp()
    await app.start()
    app.orchestrator.register_agent("sentinel", SentinelAgent(), role="sentinel")
    app.orchestrator.register_agent("nexus", NexusAgent(), role="nexus")
    app.orchestrator.register_agent("vortex", VortexAgent(), role="vortex")
    app.orchestrator.register_agent("apolo", ApoloAgent(), role="apolo")

    # 1. Health check
    health = await app.get_health()
    print("Health:", json.dumps(health, indent=2, ensure_ascii=False))

    # 2. Decision with auto-legal
    r1 = await app.process_decision(
        title="Sistema de IA com dados pessoais",
        description="Plataforma que usa IA para perfil de consumidor com dados sensiveis",
        context={"stack": ["python", "docker", "openai"]},
        priority=8,
    )
    print("\nDecision verdict:", r1.get("verdict"))
    print("Decision confidence:", r1.get("confidence"))
    if r1.get("legal_analysis") and "opinion" in r1["legal_analysis"]:
        op = r1["legal_analysis"]["opinion"]
        print("Legal veredito:", op.get("veredito"))
        print("Legal risco:", op.get("risco"))
        print("Leis aplicaveis:", len(op.get("leis_aplicaveis", [])))
        for lei in op.get("leis_aplicaveis", [])[:3]:
            print(f"  -> {lei['lei']}: {lei['titulo']}")

    # 3. Meta analysis
    meta = await app.run_meta_analysis()
    si = meta["self_improver"]
    au = meta["auditor"]
    op = meta["optimizer"]
    an = meta["analyst"]
    print("\nMeta analysis:")
    print(f"  SelfImprove: {si.get('total_suggestions', 0)} suggestions, health={si.get('system_health_score', 'N/A')}")
    print(f"  Auditor: {au.get('total_violations', 0)} violations, score={au.get('compliance_score', 'N/A')}")
    print(f"  Optimizer: {op.get('total_optimizations', 0)} optimizations")
    print(f"  Analyst: {an.get('patterns_found', 0)} patterns, {len(an.get('insights', []))} insights")

    # 4. Report
    report = await app.generate_report()
    print(f"\nReport #{report['report_id']}")
    print(f"  Decisions: {len(report['decision_history'])}")
    print(f"  Legal analyses: {report['legal_department']['total_analyses']}")

    # 5. Worker stats
    import redis.asyncio as aioredis
    r = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    worker_stats = await r.get("cupula:worker:stats")
    if worker_stats:
        print(f"\nWorker stats: {json.loads(worker_stats)}")

    await app.stop()
    print("\nALL DONE!")


if __name__ == "__main__":
    asyncio.run(test_full())
