from typing import Literal, Optional
from pydantic import BaseModel, Field


class OllamaCloudConfig(BaseModel):
    """Configuration for a locally-running Ollama instance."""
    provider: Literal["ollama"]
    model: str
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 120


class AnthropicCloudConfig(BaseModel):
    """Configuration for the Anthropic API (direct or via proxy)."""
    provider: Literal["anthropic"]
    model: str
    # Where the real LLM proxy will live in production.
    # Ignored when use_proxy=False (current prototype behaviour).
    proxy_endpoint: str = "http://llm-proxy.internal/v1"
    # Name of the environment variable that holds the API key.
    api_key_env: str = "ANTHROPIC_API_KEY"
    # False → call Anthropic API directly (prototype mode)
    # True  → route through proxy_endpoint (production mode)
    use_proxy: bool = False


# Union type — discriminated on the `provider` field
LLMCloudConfig = OllamaCloudConfig | AnthropicCloudConfig


class AdminDefaults(BaseModel):
    """Default values applied when an agent spec omits a field."""
    llm_cloud: str = "ollama-llama3"


class AdminConfig(BaseModel):
    """Top-level admin configuration loaded from admin_config.yaml."""
    llm_clouds: dict[str, OllamaCloudConfig | AnthropicCloudConfig] = Field(default_factory=dict)
    defaults: AdminDefaults = Field(default_factory=AdminDefaults)

    def get_cloud(self, name: str | None) -> OllamaCloudConfig | AnthropicCloudConfig:
        key = name or self.defaults.llm_cloud
        if key not in self.llm_clouds:
            raise ValueError(
                f"LLM cloud '{key}' not found in admin config. "
                f"Available: {list(self.llm_clouds.keys())}"
            )
        return self.llm_clouds[key]
