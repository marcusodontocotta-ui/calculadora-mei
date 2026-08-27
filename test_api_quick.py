import asyncio
import httpx
import json

BASE = "http://127.0.0.1:8080/api/v1"


async def test_api():
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get(f"{BASE}/health")
            print(f"GET /health -> {r.status_code}")
            print(f"  Body: {r.text[:500]}")
        except Exception as e:
            print(f"Health error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api())
