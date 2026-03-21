from __future__ import annotations

from app.config import get_settings, AnthropicCloudConfig, OllamaCloudConfig
from app.llm.base import BaseLLMProxy
from app.llm.anthropic_proxy import AnthropicProxy
from app.llm.ollama_proxy import OllamaProxy


def build_llm_proxy(cloud_name: str | None = None) -> BaseLLMProxy:
    settings = get_settings()
    cloud = settings.admin_config.get_cloud(cloud_name or settings.llm_cloud)
    if isinstance(cloud, AnthropicCloudConfig):
        return AnthropicProxy(cloud)
    elif isinstance(cloud, OllamaCloudConfig):
        return OllamaProxy(cloud)
    raise ValueError(f"Unknown LLM provider: {cloud.provider}")
