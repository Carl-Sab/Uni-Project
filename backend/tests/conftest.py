import os

# Importing app.scripts.verify_data pulls in app.config, which builds
# Settings eagerly at import time. Tests exercise pure functions only and
# never touch a real database, so these just need to be present.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test")
os.environ.setdefault("ADMIN_USERNAME", "test")
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("PYDANTIC_AI_GATEWAY_API_KEY", "test")
