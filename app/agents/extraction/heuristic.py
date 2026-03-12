"""
Heuristic extraction strategy.

Uses regex and keyword pattern matching to extract field values from the
conversation — no additional LLM calls.

Advantages:
  - Zero extra LLM calls (fast, cheap)
  - Deterministic and easy to debug
  - Works even when the LLM ignores JSON-block instructions

Disadvantages:
  - Only reliable for enum fields (exact option matching)
  - Poor accuracy for freeform text fields
  - Misses nuanced or paraphrased answers

Recommended when:
  - The agent spec uses mostly enum fields
  - Speed / cost is the primary concern
  - Used as a fallback layer alongside json_block
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy, LLMMessage
    from app.models.spec import MetadataField

from .base import ExtractionStrategy


class HeuristicExtractor(ExtractionStrategy):
    """Pattern-based extraction — no extra LLM calls."""

    async def extract(
        self,
        agent_reply: str,
        conversation_history: list["LLMMessage"],
        fields: list["MetadataField"],
        llm_proxy: "BaseLLMProxy | None" = None,
    ) -> dict[str, Any]:
        # Scan the most recent user message for matches
        user_messages = [m.content for m in conversation_history if m.role == "user"]
        if not user_messages:
            return {}

        recent_user_text = user_messages[-1].lower()
        extracted: dict[str, Any] = {}

        for field in fields:
            if field.type == "enum" and field.options:
                for option in field.options:
                    if option.lower() in recent_user_text:
                        extracted[field.field] = option
                        break

            elif field.type == "boolean":
                if any(w in recent_user_text for w in ["yes", "yeah", "yep", "correct", "true"]):
                    extracted[field.field] = True
                elif any(w in recent_user_text for w in ["no", "nope", "not", "false"]):
                    extracted[field.field] = False

            elif field.type in ("integer", "float"):
                # Extract first number found in the message
                match = re.search(r"\b(\d+(?:\.\d+)?)\b", recent_user_text)
                if match:
                    val = match.group(1)
                    try:
                        extracted[field.field] = (
                            int(val) if field.type == "integer" else float(val)
                        )
                    except ValueError:
                        pass

        return extracted
