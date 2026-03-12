"""Abstract base class for extraction strategies — kept separate to avoid circular imports."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy, LLMMessage
    from app.models.spec import MetadataField


class ExtractionStrategy(ABC):
    @abstractmethod
    async def extract(
        self,
        agent_reply: str,
        conversation_history: list["LLMMessage"],
        fields: list["MetadataField"],
        llm_proxy: "BaseLLMProxy | None" = None,
    ) -> dict[str, Any]:
        """Return a dict of {field_name: value} for any fields newly collected."""
        ...
