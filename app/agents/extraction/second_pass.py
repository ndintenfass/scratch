"""
Second-pass extraction strategy.

After the main LLM response is generated, a second LLM call is made that
asks the model to extract structured field values from the full conversation
so far.

Advantages:
  - More reliable extraction — the extraction call is focused solely on
    structured data, not conversational quality
  - Works with models that don't reliably follow JSON-block instructions
  - The full conversation context is available for holistic extraction

Disadvantages:
  - Doubles LLM calls per turn (latency + cost)
  - Extracted values may lag by one turn (conversation history may not
    yet include the just-returned assistant message)

Recommended when:
  - Using a smaller local model that struggles with json_block
  - High data accuracy is more important than speed
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy, LLMMessage
    from app.models.spec import MetadataField

from .base import ExtractionStrategy
from app.llm.base import LLMRequest, LLMMessage as _LLMMessage


def _build_extraction_prompt(
    fields: list["MetadataField"],
    conversation_history: list["LLMMessage"],
    agent_reply: str,
) -> str:
    field_descriptions = "\n".join(
        f"  - {f.field} ({f.type}): {f.description}"
        + (f" [options: {f.options}]" if f.options else "")
        for f in fields
    )

    history_text = "\n".join(
        f"{m.role.upper()}: {m.content}" for m in conversation_history
    )
    if agent_reply:
        history_text += f"\nASSISTANT: {agent_reply}"

    return (
        f"You are a data extraction assistant. Based on the conversation below, "
        f"extract any field values that have been clearly established.\n\n"
        f"Fields to extract:\n{field_descriptions}\n\n"
        f"Conversation:\n{history_text}\n\n"
        f"Reply ONLY with valid JSON in this exact format (no prose, no markdown fences):\n"
        f'{{ "extracted": {{ "field_name": "value_or_null" }} }}\n'
        f"Only include fields you are confident about. Omit uncertain fields entirely."
    )


class SecondPassExtractor(ExtractionStrategy):
    """Makes a second LLM call to extract structured fields from the conversation."""

    async def extract(
        self,
        agent_reply: str,
        conversation_history: list["LLMMessage"],
        fields: list["MetadataField"],
        llm_proxy: "BaseLLMProxy | None" = None,
    ) -> dict[str, Any]:
        if llm_proxy is None:
            return {}

        prompt = _build_extraction_prompt(fields, conversation_history, agent_reply)
        request = LLMRequest(
            messages=[_LLMMessage(role="user", content=prompt)],
            model="",  # will use whatever the proxy has configured
            max_tokens=512,
            temperature=0.0,  # deterministic for extraction
        )

        try:
            response = await llm_proxy.complete(request)
            data = json.loads(response.content.strip())
            return data.get("extracted", {})
        except (json.JSONDecodeError, Exception):
            return {}
