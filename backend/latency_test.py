import asyncio
import time

from app.db import async_session
from app.redis_client import redis
from app.services.retrieval import _retrieval_cache_key, hybrid_search

QUERY = "What happens if I fail a course and have to repeat it?"


async def main():
    await redis.delete(_retrieval_cache_key(QUERY))

    async with async_session() as session:
        t0 = time.perf_counter()
        await hybrid_search(session, QUERY)
        cold_ms = (time.perf_counter() - t0) * 1000

    async with async_session() as session:
        t0 = time.perf_counter()
        await hybrid_search(session, QUERY)
        warm_ms = (time.perf_counter() - t0) * 1000

    print(f"retrieval cold (miss): {cold_ms:.1f} ms")
    print(f"retrieval warm (hit):  {warm_ms:.1f} ms")


if __name__ == "__main__":
    asyncio.run(main())
