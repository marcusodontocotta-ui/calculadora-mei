import httpx, json
BASE = "http://127.0.0.1:8080/api/v1"
with httpx.Client(timeout=10) as c:
    h = c.get(f"{BASE}/health").json()
    w = c.get(f"{BASE}/worker/stats").json().get("worker", {})
    lb = c.get(f"{BASE}/leaderboard").json().get("leaderboard", [])
    ls = c.get(f"{BASE}/legal/stats").json().get("stats", {})
    print("=== HEALTH ===")
    print(json.dumps(h, indent=2, default=str))
    print()
    print("=== WORKER ===")
    print(json.dumps(w, indent=2, default=str))
    print()
    print("=== LEADERBOARD ===")
    for a in lb:
        print(f"  #{a['rank']} {a['agent_id']:10s} score={a['overall_score']:.4f} tasks={a['total_tasks']}")
    print()
    print("=== LEGAL STATS ===")
    print(json.dumps(ls, indent=2, default=str))
