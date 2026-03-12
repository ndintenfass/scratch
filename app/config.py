"""
Loads and validates the admin_config.yaml file.

The path is resolved from the ADMIN_CONFIG_PATH environment variable
(defaults to 'admin_config.yaml' in the current working directory).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models.admin import AdminConfig, OllamaCloudConfig, AnthropicCloudConfig


def load_admin_config(path: str | None = None) -> AdminConfig:
    """
    Load and validate admin_config.yaml.

    Args:
        path: path to the YAML file. Defaults to the ADMIN_CONFIG_PATH
              environment variable, then 'admin_config.yaml'.

    Returns:
        Validated AdminConfig instance.

    Raises:
        FileNotFoundError: if the config file does not exist.
        ValidationError:   if the config fails Pydantic validation.
    """
    config_path = Path(path or os.environ.get("ADMIN_CONFIG_PATH", "admin_config.yaml"))
    if not config_path.exists():
        raise FileNotFoundError(
            f"Admin config not found at: {config_path.resolve()}. "
            "Set ADMIN_CONFIG_PATH or run from the project root."
        )

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    # Deserialise each cloud config with the correct typed subclass
    raw_clouds = raw.get("llm_clouds", {})
    typed_clouds: dict[str, OllamaCloudConfig | AnthropicCloudConfig] = {}
    for name, cloud_data in raw_clouds.items():
        provider = cloud_data.get("provider", "")
        if provider == "ollama":
            typed_clouds[name] = OllamaCloudConfig(**cloud_data)
        elif provider == "anthropic":
            typed_clouds[name] = AnthropicCloudConfig(**cloud_data)
        else:
            raise ValueError(
                f"Unknown provider '{provider}' for cloud '{name}' in admin_config.yaml. "
                "Supported: ollama, anthropic"
            )

    raw["llm_clouds"] = typed_clouds

    # Allow DEFAULT_LLM_CLOUD env var to override the default cloud.
    # This is how Render (and other cloud environments) select a cloud
    # without editing admin_config.yaml (which defaults to local Ollama).
    override = os.environ.get("DEFAULT_LLM_CLOUD")
    if override:
        if override not in typed_clouds:
            raise ValueError(
                f"DEFAULT_LLM_CLOUD='{override}' is not defined in admin_config.yaml. "
                f"Available clouds: {list(typed_clouds.keys())}"
            )
        raw.setdefault("defaults", {})["llm_cloud"] = override

    return AdminConfig(**raw)
