"""
Abstract base class for LLM proxy implementations.

This is the primary extension point for the system. All LLM calls in
agents go through a BaseLLMProxy subclass — swap the implementation to
change which model or proxy is used, without touching any agent code.

In production, a single HTTP proxy will sit here, receiving requests
from all agents and forwarding them to the appropriate LLM provider.
This file defines the contract that proxy must honour.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """A single message in a conversation."""
    role: str  # "user", "assistant", or "system"
    content: str


class LLMRequest(BaseModel):
    """
    Normalised request sent to any LLM via the proxy.

    The proxy translates this into the provider-specific format
    (Anthropic messages API, Ollama /api/chat, etc.).
    """
    messages: list[LLMMessage]
    system: Optional[str] = None  # system prompt (separate from the message list)
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7


class LLMResponse(BaseModel):
    """
    Normalised response returned by any LLM via the proxy.
    """
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMProxy(ABC):
    """
    Abstract LLM proxy. All agent LLM calls go through this interface.

    The concrete implementation determines whether requests are:
      - Answered by a local Ollama model (OllamaProxy)
      - Answered by the Anthropic API directly (AnthropicProxy)
      - Forwarded to a shared infrastructure proxy (future production proxy)
      - Answered with stub responses (MockLLMProxy for unit tests)
    """

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Send a completion request and return the response.
        Must be implemented by all concrete proxy classes.
        """
        ...
