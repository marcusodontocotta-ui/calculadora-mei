import asyncio
from cupula.config.settings import get_settings

async def test():
    settings = get_settings()
    print("Testing legal gateway connection...", flush=True)
    
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await r.ping()
    print("Redis ping OK", flush=True)
    
    from cupula.legal_gateway.laws.database import LegalDB
    db = LegalDB(r)
    print("LegalDB created", flush=True)
    
    await db.init()
    print(f"LegalDB init OK, {db._count_laws()} laws", flush=True)
    
    await r.aclose()
    print("All done!", flush=True)

asyncio.run(test())
