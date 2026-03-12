"""
Admin API routes — server configuration and status.

Routes:
  GET /admin/config   Return loaded LLM cloud registry and active defaults
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config")
async def get_admin_config(request: Request) -> dict[str, Any]:
    """
    Return the current admin configuration: configured LLM clouds and the
    active default cloud (accounting for any DEFAULT_LLM_CLOUD env override).
    """
    admin_config = request.app.state.admin_config

    clouds: dict[str, dict[str, Any]] = {}
    for name, cloud in admin_config.llm_clouds.items():
        entry: dict[str, Any] = {
            "provider": cloud.provider,
            "model": cloud.model,
        }
        if cloud.provider == "ollama":
            entry["base_url"] = cloud.base_url  # type: ignore[union-attr]
        elif cloud.provider == "anthropic":
            entry["use_proxy"] = cloud.use_proxy  # type: ignore[union-attr]
        clouds[name] = entry

    env_override = os.environ.get("DEFAULT_LLM_CLOUD")

    return {
        "default_llm_cloud": admin_config.defaults.llm_cloud,
        "env_override": env_override,
        "llm_clouds": clouds,
    }
