import asyncio
import httpx
import json

BASE = "http://127.0.0.1:8080/api/v1"

async def test(name, method, url, payload=None):
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            if method == "GET":
                r = await c.get(url)
            else:
                r = await c.post(url, json=payload)
            print(f"\n{'='*60}")
            print(f"  {name}")
            print(f"  {method} {url.replace(BASE,'')}")
            print(f"  Status: {r.status_code}")
            body = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text[:300]}
            print(f"  Body: {json.dumps(body, indent=2, ensure_ascii=False)[:600]}")
        except Exception as e:
            print(f"\n  {name}: ERROR - {e}")


async def main():
    print("=" * 60)
    print("  CUPULA API - FULL TEST")
    print("=" * 60)

    await test("Health", "GET", f"{BASE}/health")
    await test("Status", "GET", f"{BASE}/status")
    await test("Leaderboard", "GET", f"{BASE}/leaderboard")
    await test("Legal Stats", "GET", f"{BASE}/legal/stats")
    await test("AI Capabilities", "GET", f"{BASE}/ai/capabilities")

    await test("Decision", "POST", f"{BASE}/decide", {
        "title": "Implantar sistema de pagamentos via PIX",
        "description": "Desenvolver integração com gateway de pagamento usando PIX para e-commerce. "
                       "Envolve dados pessoais (LGPD), relação com consumidor (CDC), e obrigações tributárias (nota fiscal).",
        "priority": 8,
        "auto_legal": True,
    })

    await test("Legal Analysis", "POST", f"{BASE}/legal/analyze", {
        "titulo": "Coleta de dados de navegação para perfil de usuario",
        "descricao": "Sistema de rastreamento de comportamento do usuario para personalização de conteúdo",
        "dominios": ["dados_pessoais", "digital"],
        "acao_proposta": "Coletar dados de navegação e criar perfil comportamental",
    })

    await test("Report", "GET", f"{BASE}/report")
    await test("Meta Analysis", "GET", f"{BASE}/meta/analyze")

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETE")
    print("=" * 60)


asyncio.run(main())
