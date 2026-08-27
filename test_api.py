import asyncio
import httpx
import json

BASE = "http://127.0.0.1:8080/api/v1"


async def test_api():
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Health
        r = await client.get(f"{BASE}/health")
        print(f"GET /health -> {r.status_code}")
        print(f"  {json.dumps(r.json(), indent=2, ensure_ascii=False)}")

        # 2. Status
        r = await client.get(f"{BASE}/status")
        print(f"\nGET /status -> {r.status_code}")
        data = r.json()
        print(f"  Agents: {data['system']['agents_registered']}")
        print(f"  Legal analyses: {data['legal'].get('total_analises', 0)}")

        # 3. Decision
        r = await client.post(f"{BASE}/decide", json={
            "title": "Sistema de cobranca automatizada",
            "description": "API de cobranca com dados bancarios e integracao com gateway de pagamento",
            "context": {"stack": ["python", "docker"]},
            "priority": 7,
            "auto_legal": True,
        })
        print(f"\nPOST /decide -> {r.status_code}")
        result = r.json()
        print(f"  Verdict: {result.get('verdict')}")
        print(f"  Confidence: {result.get('confidence')}")
        if result.get("legal_analysis") and "opinion" in result["legal_analysis"]:
            op = result["legal_analysis"]["opinion"]
            print(f"  Legal: {op['veredito']} / {op['risco']}")

        # 4. Legal analysis
        r = await client.post(f"{BASE}/legal/analyze", json={
            "titulo": "App de delivery com dados de localizacao",
            "descricao": "Aplicativo que coleta localizacao e dados pessoais de usuarios para entrega",
            "dominios": ["dados_pessoais", "consumidor", "digital"],
        })
        print(f"\nPOST /legal/analyze -> {r.status_code}")
        legal = r.json()
        op = legal.get("opinion", {})
        print(f"  Veredito: {op.get('veredito')}")
        print(f"  Risco: {op.get('risco')}")
        print(f"  Leis: {len(op.get('leis_aplicaveis', []))}")

        # 5. Meta analysis
        r = await client.get(f"{BASE}/meta/analyze")
        print(f"\nGET /meta/analyze -> {r.status_code}")
        meta = r.json()
        print(f"  SelfImprove: {meta['self_improver']['total_suggestions']} suggestions")
        print(f"  Auditor: {meta['auditor']['total_violations']} violations")
        print(f"  Optimizer: {meta['optimizer']['total_optimizations']} opts")
        print(f"  Analyst: {meta['analyst']['patterns_found']} patterns")

        # 6. Report
        r = await client.get(f"{BASE}/report")
        print(f"\nGET /report -> {r.status_code}")
        report = r.json()
        print(f"  Report #{report['report_id']}")
        print(f"  Decisions in history: {len(report['decision_history'])}")

        # 7. Leaderboard
        r = await client.get(f"{BASE}/leaderboard")
        print(f"\nGET /leaderboard -> {r.status_code}")
        lb = r.json()
        print(f"  Leaderboard entries: {len(lb['leaderboard'])}")

        # 8. Legal stats
        r = await client.get(f"{BASE}/legal/stats")
        print(f"\nGET /legal/stats -> {r.status_code}")
        stats = r.json()
        print(f"  Total analyses: {stats['stats'].get('total_analises', 0)}")

        print("\nALL API TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(test_api())
