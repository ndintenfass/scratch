"""
LLM proxy layer — the single seam through which all LLM calls pass.

In production this layer will route every request through a shared
infrastructure proxy. In development/prototype mode it calls providers
directly (or uses a local Ollama instance).

To add a new provider:
  1. Create a new class in this package that inherits BaseLLMProxy
  2. Register it in get_proxy() below
"""
from .base import BaseLLMProxy, LLMMessage, LLMRequest, LLMResponse
from .mock import MockLLMProxy
from .ollama_proxy import OllamaProxy
from .anthropic_proxy import AnthropicProxy

from app.models.admin import OllamaCloudConfig, AnthropicCloudConfig


def get_proxy(cloud_config: OllamaCloudConfig | AnthropicCloudConfig) -> BaseLLMProxy:
    """Factory: returns the appropriate proxy implementation for a cloud config."""
    if isinstance(cloud_config, OllamaCloudConfig):
        return OllamaProxy(cloud_config)
    if isinstance(cloud_config, AnthropicCloudConfig):
        return AnthropicProxy(cloud_config)
    raise ValueError(f"No proxy implementation for provider: {cloud_config.provider}")


__all__ = [
    "BaseLLMProxy",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "MockLLMProxy",
    "OllamaProxy",
    "AnthropicProxy",
    "get_proxy",
]
