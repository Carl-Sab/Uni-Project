import asyncio
import sys
import os

# asyncpg's connection cleanup interacts badly with Windows' default
# ProactorEventLoop (AttributeError during socket teardown after the test's
# event loop closes). The selector loop doesn't have this problem.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Importing app.services.academic (and anything that pulls in app.config)
# builds Settings eagerly at import time. The pure unit tests never touch a
# database, but the integration tests in test_students_integration.py do -
# they expect the docker-compose postgres/redis to be up and loaded via
# `uv run python -m app.scripts.load_data` (see README). These defaults
# match the host-side port mapping in docker-compose.yml.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/university_assistant"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("PYDANTIC_AI_GATEWAY_API_KEY", "test")

import pytest_asyncio


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _dispose_engine_at_session_end():
    yield
    from app.db import engine

    await engine.dispose()
