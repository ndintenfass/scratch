"""
JSON Block extraction strategy (default).

The agent's system prompt instructs the LLM to append a fenced JSON block
at the end of every reply:

    ```json
    {"extracted": {"field_name": "value", ...}}
    ```

This extractor strips that block from the visible reply and parses the
field values. The LLM should only include fields it has actually collected
in the current conversation turn.

Advantages:
  - Single LLM call per turn
  - The LLM self-reports confidence (it decides what to include)
  - Clean separation of prose reply and structured data

Disadvantages:
  - Relies on the model following the instruction reliably
  - Some smaller models may not consistently produce valid JSON
  - If the model fails, falls back gracefully to an empty dict
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy, LLMMessage
    from app.models.spec import MetadataField

from .base import ExtractionStrategy

# Matches the last ```json ... ``` block in the response
_JSON_BLOCK_RE = re.compile(
    r"```json\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


def strip_extraction_block(text: str) -> tuple[str, dict[str, Any]]:
    """
    Split the LLM response into (clean_reply, extracted_fields).

    Returns the prose without the JSON block, and the extracted dict.
    If no valid block is found, returns the original text and an empty dict.
    """
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return text.strip(), {}

    try:
        data = json.loads(match.group(1))
        extracted = data.get("extracted", {})
        if not isinstance(extracted, dict):
            extracted = {}
    except json.JSONDecodeError:
        extracted = {}

    clean = text[: match.start()].rstrip() + text[match.end() :]
    return clean.strip(), extracted


EXTRACTION_INSTRUCTIONS = """
After your conversational response, append a fenced JSON block with any field values you have confidently collected IN THIS TURN OR SO FAR. Use exactly this format (do not include markdown or explanation inside the block):

```json
{"extracted": {"field_name": "value"}}
```

Rules:
- Only include fields where you are confident in the value.
- Omit fields you have not yet gathered.
- Use null for a field only if the user explicitly said they don't have/know it.
- The block must be the very last thing in your response.
"""


class JsonBlockExtractor(ExtractionStrategy):
    """Parses a ```json {"extracted": {...}}``` block appended by the LLM."""

    @property
    def system_prompt_addon(self) -> str:
        """Appended to the interview bot's system prompt to instruct the LLM."""
        return EXTRACTION_INSTRUCTIONS

    async def extract(
        self,
        agent_reply: str,
        conversation_history: list["LLMMessage"],
        fields: list["MetadataField"],
        llm_proxy: "BaseLLMProxy | None" = None,
    ) -> dict[str, Any]:
        _, extracted = strip_extraction_block(agent_reply)
        return extracted
