"""text-embedding-3-small via the Pydantic AI Gateway.

Verified directly against the gateway before any of this was written: the
OpenAI-shaped provider client the gateway hands back supports
`.embeddings.create(...)` and returns real 1536-dim vectors, so this calls
it the same way the plain OpenAI SDK would - no separate embeddings-specific
gateway API was needed.
"""

from openai import AsyncOpenAI
from pydantic_ai.providers.gateway import gateway_provider

from app.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def _client() -> AsyncOpenAI:
    provider = gateway_provider("openai", api_key=settings.PYDANTIC_AI_GATEWAY_API_KEY)
    return provider.client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _client()
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


async def embed_text(text: str) -> list[float]:
    (embedding,) = await embed_texts([text])
    return embedding
