from __future__ import annotations

import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Literal, Optional


class OllamaCloudConfig(BaseModel):
    provider: Literal["ollama"]
    model: str
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 120


class AnthropicCloudConfig(BaseModel):
    provider: Literal["anthropic"]
    model: str
    proxy_endpoint: str = "http://llm-proxy.internal/v1"
    api_key_env: str = "ANTHROPIC_API_KEY"
    use_proxy: bool = False


LLMCloudConfig = OllamaCloudConfig | AnthropicCloudConfig


class AdminDefaults(BaseModel):
    llm_cloud: str = "anthropic-claude-haiku"


class AdminConfig(BaseModel):
    llm_clouds: dict[str, OllamaCloudConfig | AnthropicCloudConfig] = {}
    defaults: AdminDefaults = AdminDefaults()

    def get_cloud(self, name: str | None = None) -> LLMCloudConfig:
        key = name or self.defaults.llm_cloud
        if key not in self.llm_clouds:
            raise ValueError(f"LLM cloud '{key}' not found. Available: {list(self.llm_clouds.keys())}")
        return self.llm_clouds[key]


class Settings(BaseModel):
    database_url: str = "sqlite+aiosqlite:///./democracy.db"
    secret_key: str = "dev-secret-key-change-in-production"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    llm_cloud: str = "anthropic-claude-haiku"
    vote_threshold: int = 1_000_000
    base_url: str = "http://localhost:8000"
    admin_config: AdminConfig = AdminConfig()

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(__file__).parent.parent
        admin_config = AdminConfig()
        config_path = base_dir / "admin_config.yaml"
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text())
            if raw:
                admin_config = AdminConfig.model_validate(raw)

        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./democracy.db"),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password=os.getenv("ADMIN_PASSWORD", "changeme"),
            llm_cloud=os.getenv("LLM_CLOUD", admin_config.defaults.llm_cloud),
            vote_threshold=int(os.getenv("VOTE_THRESHOLD", "1000000")),
            base_url=os.getenv("BASE_URL", "http://localhost:8000"),
            admin_config=admin_config,
        )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
