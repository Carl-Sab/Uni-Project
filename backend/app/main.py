from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.redis_client import redis

app = FastAPI(title="University Assistant API")


@app.get("/health")
async def health():
    postgres_ok = False
    redis_ok = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if postgres_ok and redis_ok else "degraded",
        "postgres": "ok" if postgres_ok else "unreachable",
        "redis": "ok" if redis_ok else "unreachable",
    }
