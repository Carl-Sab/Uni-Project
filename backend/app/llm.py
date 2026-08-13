"""Model factory for building PydanticAI models via the Pydantic AI Gateway.

Not wired up anywhere yet — the admin panel will use this later to let an
administrator switch the assistant's model without a redeploy.
"""

from typing import Literal

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.gateway import gateway_provider

from app.config import settings

Provider = Literal["anthropic", "openai", "google"]


def get_model(provider: Provider, model_name: str) -> Model:
    gateway = gateway_provider(provider, api_key=settings.PYDANTIC_AI_GATEWAY_API_KEY)

    if provider == "anthropic":
        return AnthropicModel(model_name, provider=gateway)
    if provider == "openai":
        return OpenAIChatModel(model_name, provider=gateway)
    if provider == "google":
        return GoogleModel(model_name, provider=gateway)

    raise ValueError(f"Unsupported provider: {provider}")
