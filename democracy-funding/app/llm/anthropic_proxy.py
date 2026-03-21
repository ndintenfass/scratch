from __future__ import annotations

import os
import httpx
import anthropic

from .base import BaseLLMProxy, LLMRequest, LLMResponse
from app.config import AnthropicCloudConfig


class AnthropicProxy(BaseLLMProxy):
    def __init__(self, config: AnthropicCloudConfig) -> None:
        self.config = config

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if self.config.use_proxy:
            return await self._via_proxy(request)
        return await self._direct(request)

    async def _direct(self, request: LLMRequest) -> LLMResponse:
        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            raise EnvironmentError(
                f"Environment variable '{self.config.api_key_env}' is not set."
            )
        client = anthropic.AsyncAnthropic(api_key=api_key)
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        kwargs: dict = {
            "model": self.config.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
        }
        if request.system:
            kwargs["system"] = request.system
        response = await client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=self.config.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def _via_proxy(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.config.proxy_endpoint}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
