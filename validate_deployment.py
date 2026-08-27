"""
Script de Validação de Deployment — Cúpula de Gestão Autônoma

Uso: python validate_deployment.py [--url http://localhost:8080]

Verifica:
1. Conectividade Redis
2. API respondendo
3. Agentes registrados
4. Setor Jurídico funcionando
5. AI Gateway conectado
6. Worker rodando
7. Webhooks operacionais
8. Integração completa (decisão + legal + meta)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import time
import json
import httpx

BASE = "http://localhost:8080/api/v1"
PASS = 0
FAIL = 0
ERRORS = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        ERRORS.append(f"{name}: {detail}")
        print(f"  [FAIL] {name} -- {detail}")


def get(path, **kwargs):
    try:
        r = httpx.get(f"{BASE}{path}", timeout=30, **kwargs)
        return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(path, data=None, **kwargs):
    try:
        r = httpx.post(f"{BASE}{path}", json=data, timeout=60, **kwargs)
        return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    global BASE
    if len(sys.argv) > 2 and sys.argv[1] == "--url":
        BASE = sys.argv[2].rstrip("/") + "/api/v1"

    print("=" * 60)
    print("  CÚPULA — Validação de Deployment")
    print("=" * 60)
    print(f"  Target: {BASE}")
    print()

    # 1. API Health
    print("--- API ---")
    code, data = get("/health")
    check("API respondendo", code == 200, f"status={code}")
    if code == 200:
        check("Redis conectado", data.get("redis") == "connected", f"redis={data.get('redis')}")
        check("4 builtin agents", data.get("agents_registered", 0) == 4, f"count={data.get('agents_registered')}")
        check("5 legal agents", data.get("legal_agents_registered", 0) == 5, f"count={data.get('legal_agents_registered')}")
        check("20 leis indexadas", data.get("legal_db_laws", 0) == 20, f"laws={data.get('legal_db_laws')}")
        check("AI Gateway conectado", data.get("ai_gateway") == "connected", f"gw={data.get('ai_gateway')}")
        check("3 AI capabilities", data.get("ai_capabilities", 0) == 3, f"caps={data.get('ai_capabilities')}")

    # 2. Agentes
    print("\n--- AGENTES ---")
    code, data = get("/status")
    check("Status endpoint", code == 200)
    if code == 200:
        agents = data.get("system", {}).get("agents", {})
        for name in ["sentinel", "nexus", "vortex", "apolo"]:
            check(f"Agente {name}", name in agents, f"agents={list(agents.keys())}")

    # 3. Leaderboard
    print("\n--- REPUTAÇÃO ---")
    code, data = get("/leaderboard")
    check("Leaderboard", code == 200 and len(data.get("leaderboard", [])) == 4)

    # 4. Legal
    print("\n--- SETOR JURÍDICO ---")
    code, data = get("/legal/stats")
    check("Legal stats", code == 200)
    code, data = post("/legal/analyze", {
        "titulo": "Teste de deploy",
        "descricao": "Validação automática de deployment",
        "dominios": ["digital"],
    })
    check("Legal analysis", code == 200 and "opinion" in data, f"keys={list(data.keys())[:5]}")

    # 5. AI Capabilities
    print("\n--- AI GATEWAY ---")
    code, data = get("/ai/capabilities")
    check("AI capabilities list", code == 200 and data.get("ai_gateway") == "connected")

    # 6. Worker
    print("\n--- WORKER ---")
    code, data = get("/worker/stats")
    check("Worker stats", code == 200 and data.get("worker", {}).get("running"))
    if code == 200 and data.get("worker"):
        check("Cron rodando", data["worker"].get("cron_runs", 0) > 0)

    # 7. Decision (full integration)
    print("\n--- INTEGRAÇÃO COMPLETA ---")
    code, data = post("/decide", {
        "title": "Teste de validação de deployment",
        "description": "Decisão de teste para validar que todos os agentes funcionam juntos",
        "priority": 3,
        "auto_legal": True,
    })
    check("Decisão processada", code == 200 and "verdict" in data, f"verdict={data.get('verdict')}")
    if code == 200:
        check("Legal automático disparado", data.get("legal_analysis") is not None)
        check("4 respostas de agentes", data.get("responses_count", 0) == 4)
        check("Confiabilidade > 0", data.get("confidence", 0) > 0)

    # 8. Webhooks
    print("\n--- WEBHOOKS ---")
    code, data = post("/webhook/decision", {
        "title": "Teste webhook",
        "description": "Validação de webhook",
    })
    check("Webhook decision", code == 200)

    code, data = post("/webhook/n8n", {"action": "get_report"})
    check("Webhook n8n", code == 200 and "report_id" in data)

    # 9. Report + Meta
    print("\n--- RELATÓRIOS ---")
    code, data = get("/report")
    check("Report", code == 200 and "report_id" in data)

    code, data = get("/meta/analyze")
    check("Meta analysis", code == 200 and "self_improver" in data)

    # Summary
    print()
    print("=" * 60)
    total = PASS + FAIL
    print(f"  Resultado: {PASS}/{total} passaram, {FAIL} falharam")
    if ERRORS:
        print()
        print("  Erros:")
        for e in ERRORS:
            print(f"    - {e}")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
