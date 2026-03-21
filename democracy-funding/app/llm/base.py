from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    system: Optional[str] = None
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMProxy(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...
