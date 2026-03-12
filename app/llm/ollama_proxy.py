"""
Ollama LLM proxy — routes requests to a locally-running Ollama instance.

Usage:
  1. Install Ollama: https://ollama.com/
  2. Pull a model:  ollama pull llama3.2
  3. Set provider: ollama in admin_config.yaml

Ollama runs at http://localhost:11434 by default.
No API key required — ideal for development and demos.
"""
from __future__ import annotations

import json
import httpx

from .base import BaseLLMProxy, LLMRequest, LLMResponse
from app.models.admin import OllamaCloudConfig


class OllamaProxy(BaseLLMProxy):
    """Calls the Ollama /api/chat endpoint with a locally-running model."""

    def __init__(self, config: OllamaCloudConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        messages = []

        # Ollama /api/chat takes a standard messages array.
        # Inject the system prompt as the first message if provided.
        if request.system:
            messages.append({"role": "system", "content": request.system})

        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["message"]["content"]
        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )
