import asyncio
import httpx

BASE = "http://127.0.0.1:8080/api/v1"

async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{BASE}/health")
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        print(f"Body: {r.text[:1000]}")

asyncio.run(main())
