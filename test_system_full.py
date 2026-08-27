import asyncio
import httpx
import json

BASE = "http://127.0.0.1:8080/api/v1"

async def hit(name, method, url, payload=None):
    async with httpx.AsyncClient(timeout=60) as c:
        try:
            r = await c.request(method, url, json=payload)
            status = "OK" if r.status_code == 200 else f"ERR({r.status_code})"
            body = {}
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:200]}
            short = json.dumps(body, ensure_ascii=False, default=str)
            if len(short) > 300:
                short = short[:300] + "..."
            print(f"  {status} {name:30s} {short}")
        except Exception as e:
            print(f"  ERR   {name:30s} {e}")


async def main():
    print("=" * 80)
    print("  CUPULA — SISTEMA COMPLETO: API + WORKER + WEBHOOKS")
    print("=" * 80)

    print("\n--- CORE ---")
    await hit("health", "GET", f"{BASE}/health")
    await hit("status", "GET", f"{BASE}/status")
    await hit("leaderboard", "GET", f"{BASE}/leaderboard")
    await hit("worker/stats", "GET", f"{BASE}/worker/stats")

    print("\n--- DECISAO (ativa Cúpula + Legal) ---")
    await hit("decide", "POST", f"{BASE}/decide", {
        "title": "Criar chatbot com IA para atendimento ao cliente",
        "description": "Desenvolver chatbot usando GPT para atendimento, "
                       "coletando dados pessoais do cliente (LGPD), "
                       "com garantia de conformidade (CDC).",
        "priority": 9,
        "auto_legal": True,
    })

    print("\n--- LEGAL ---")
    await hit("legal/analyze", "POST", f"{BASE}/legal/analyze", {
        "titulo": "Venda de produto com cláusula de não devolução",
        "descricao": "Produto digital sem possibilidade de devolução",
        "dominios": ["consumidor", "digital"],
    })
    await hit("legal/stats", "GET", f"{BASE}/legal/stats")

    print("\n--- AI CAPABILITIES ---")
    await hit("ai/capabilities", "GET", f"{BASE}/ai/capabilities")

    print("\n--- META-ANALYSIS ---")
    await hit("meta/analyze", "GET", f"{BASE}/meta/analyze")

    print("\n--- REPORT ---")
    await hit("report", "GET", f"{BASE}/report")

    print("\n--- WEBHOOKS ---")
    await hit("webhook/decision", "POST", f"{BASE}/webhook/decision", {
        "title": "Expandir operações para novo estado",
        "description": "Abrir filial em outro estado, envolve contratos trabalhistas (CLT) "
                       "e tributários (ICMS).",
        "priority": 7,
    })
    await hit("webhook/legal", "POST", f"{BASE}/webhook/legal", {
        "titulo": "Uso de biometria para acesso",
        "descricao": "Sistema de reconhecimento facial para controle de acesso",
        "dominios": ["dados_pessoais"],
    })
    await hit("webhook/n8n", "POST", f"{BASE}/webhook/n8n", {
        "action": "get_report",
    })
    await hit("webhook/status", "POST", f"{BASE}/webhook/status", {})

    print("\n--- WAIT 35s (cron cycle) ---")
    print("  Aguardando worker cron cycle...")
    await asyncio.sleep(35)
    await hit("worker/stats (post-cron)", "GET", f"{BASE}/worker/stats")

    print("\n" + "=" * 80)
    print("  ALL TESTS COMPLETE — SYSTEM LIVE")
    print("=" * 80)


asyncio.run(main())
