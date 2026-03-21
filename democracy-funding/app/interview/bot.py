from __future__ import annotations

import json
from typing import Any

from app.llm.base import BaseLLMProxy, LLMRequest, LLMMessage
from app.interview.spec import InterviewBotConfig, MetadataField
from app.interview.extraction import strip_extraction_block, EXTRACTION_INSTRUCTIONS


class InterviewBot:
    """
    Stateless interview bot — receives conversation state as plain dicts,
    returns updated state. DB persistence is handled by the service layer.
    """

    def __init__(self, config: InterviewBotConfig, llm_proxy: BaseLLMProxy) -> None:
        self.config = config
        self.llm = llm_proxy

    async def start(self) -> tuple[str, list[dict], dict]:
        """Returns (opening_message, initial_history, initial_fields)."""
        history: list[LLMMessage] = []
        fields: dict[str, Any] = {}
        system = self._build_system_prompt(history, fields, turn_count=0)
        response = await self.llm.complete(LLMRequest(
            messages=[LLMMessage(role="user", content="[START]")],
            system=system,
            model="",
            max_tokens=512,
        ))
        clean, _ = strip_extraction_block(response.content)
        history.append(LLMMessage(role="assistant", content=clean))
        return clean, [m.model_dump() for m in history], fields

    async def turn(
        self,
        user_message: str,
        history_raw: list[dict],
        fields: dict[str, Any],
        turn_count: int,
    ) -> tuple[str, list[dict], dict[str, Any], bool]:
        """Returns (reply, updated_history, updated_fields, is_complete)."""
        history = [LLMMessage(**m) for m in history_raw]
        history.append(LLMMessage(role="user", content=user_message))
        turn_count += 1

        system = self._build_system_prompt(history, fields, turn_count)
        response = await self.llm.complete(LLMRequest(
            messages=history,
            system=system,
            model="",
            max_tokens=1024,
        ))

        clean, new_fields = strip_extraction_block(response.content)
        fields.update({k: v for k, v in new_fields.items() if v is not None})
        history.append(LLMMessage(role="assistant", content=clean))

        is_complete = self._check_complete(fields, turn_count)
        return clean, [m.model_dump() for m in history], fields, is_complete

    def _check_complete(self, fields: dict, turn_count: int) -> bool:
        if turn_count >= self.config.max_turns:
            return True
        required = [f.field for f in self.config.metadata_to_collect if f.required]
        return all(f in fields for f in required)

    def _build_system_prompt(
        self, history: list[LLMMessage], fields: dict[str, Any], turn_count: int
    ) -> str:
        cfg = self.config
        lines: list[str] = []

        lines.append(f"You are a friendly interviewer gathering ideas about: {cfg.topic}.")
        lines.append(f"Tone: {cfg.tone}.")
        lines.append("")

        remaining_required = [
            f for f in cfg.metadata_to_collect if f.required and f.field not in fields
        ]
        all_uncollected = [f for f in cfg.metadata_to_collect if f.field not in fields]

        if self._check_complete(fields, turn_count):
            lines.append("The interview is complete. The user has provided all required information.")
            lines.append(f"Closing: {cfg.completion.closing_message}")
        else:
            if remaining_required:
                desc = ", ".join(f"{f.field} ({f.description})" for f in remaining_required)
                lines.append(f"Your goal: gather these REQUIRED fields still missing: {desc}.")
            optional = [f for f in all_uncollected if not f.required]
            if optional:
                opt_desc = ", ".join(f"{f.field} ({f.description})" for f in optional)
                lines.append(f"These optional fields are also valuable: {opt_desc}.")
            lines.append("")
            lines.append(
                "Ask ONE question at a time. Keep the conversation natural. "
                "Do not list all fields — guide organically."
            )

        if fields:
            lines.append("")
            lines.append("Information already collected:")
            for k, v in fields.items():
                lines.append(f"  - {k}: {v}")

        if turn_count == 0 and cfg.opening_hints:
            lines.append("")
            lines.append("Opening guidance:")
            for hint in cfg.opening_hints:
                lines.append(f"  - {hint}")

        if turn_count >= cfg.max_turns - 2:
            lines.append("")
            lines.append("The conversation is nearing its limit. Wrap up gracefully.")

        lines.append("")
        lines.append(EXTRACTION_INSTRUCTIONS)
        return "\n".join(lines)
