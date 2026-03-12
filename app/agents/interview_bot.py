"""
Interview Bot agent implementation.

Conducts a structured, open-ended interview to collect a defined set of
metadata fields from the user. Behaviour is entirely driven by the
InterviewBotConfig in the agent spec — no hardcoded questions.

Conversation pipeline per turn:
  1. Detect keyword triggers in user message
  2. Apply segmentation rules
  3. Append user message to history
  4. Build dynamic system prompt (persona + remaining fields + hints)
  5. Call LLM proxy
  6. Run configured ExtractionStrategy to parse field values from response
  7. Merge new fields, check completion
  8. Return clean agent reply + updated state
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .base import BaseAgent, ConversationState
from .extraction import get_extraction_strategy
from .extraction.json_block import JsonBlockExtractor, strip_extraction_block
from app.llm.base import LLMRequest, LLMMessage

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy
    from app.models.spec import AgentSpec, MetadataField


class InterviewBotAgent(BaseAgent):
    """
    An agent that conducts a structured interview to collect metadata fields.
    All behaviour is driven by the InterviewBotConfig in the agent spec.
    """

    def __init__(self, spec: "AgentSpec", llm_proxy: "BaseLLMProxy", agent_id: str) -> None:
        super().__init__(spec, llm_proxy, agent_id)
        self._config = spec.config  # type: ignore[assignment]  # InterviewBotConfig
        self._extractor = get_extraction_strategy(self._config.extraction)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def start_conversation(self) -> tuple[str, ConversationState]:
        state = ConversationState.new(self.agent_id)
        system = self._build_system_prompt(state)
        opening_request = LLMRequest(
            messages=[LLMMessage(role="user", content="[START]")],
            system=system,
            model="",
            max_tokens=512,
        )
        response = await self.llm_proxy.complete(opening_request)
        opening_message, _ = self._clean_reply(response.content)

        state.history.append(LLMMessage(role="assistant", content=opening_message))
        state.touch()
        return opening_message, state

    async def process_message(
        self,
        state: ConversationState,
        message: str,
    ) -> tuple[str, ConversationState]:
        # 1. Keyword triggers
        self._apply_keyword_triggers(state, message)

        # 2. Segmentation rules
        self._apply_segmentation_rules(state, message)

        # 3. Append user message to history
        state.history.append(LLMMessage(role="user", content=message))
        state.turn_count += 1

        # 4. Build system prompt (dynamic: includes remaining fields, hints)
        system = self._build_system_prompt(state)

        # 5. Call LLM
        response = await self.llm_proxy.complete(
            LLMRequest(
                messages=state.history,
                system=system,
                model="",
                max_tokens=1024,
            )
        )

        # 6. Extract fields from response
        raw_reply = response.content
        clean_reply, _ = self._clean_reply(raw_reply)
        new_fields = await self._extractor.extract(
            agent_reply=raw_reply,
            conversation_history=state.history,
            fields=self._config.metadata_to_collect,
            llm_proxy=self.llm_proxy,
        )

        # 7. Merge fields + check completion
        state.collected_fields.update(
            {k: v for k, v in new_fields.items() if v is not None}
        )
        state.pending_hints.clear()

        if not state.is_complete:
            state.is_complete = self._check_completion(state)

        # Append assistant reply to history (clean version without JSON block)
        state.history.append(LLMMessage(role="assistant", content=clean_reply))
        state.touch()

        return clean_reply, state

    # ------------------------------------------------------------------
    # System prompt builder
    # ------------------------------------------------------------------

    def _build_system_prompt(self, state: ConversationState) -> str:
        cfg = self._config
        lines: list[str] = []

        # --- Persona & topic ---
        lines.append(
            f"You are a friendly interviewer conducting a conversation about: {cfg.topic}."
        )
        lines.append(f"Tone: {cfg.tone}.")
        lines.append("")

        # --- Goal ---
        remaining = self._remaining_required_fields(state)
        all_uncollected = self._uncollected_fields(state)

        if state.is_complete:
            lines.append("The interview is complete. The user has provided all required information.")
            lines.append(f"Closing: {cfg.completion.closing_message}")
        else:
            if remaining:
                remaining_desc = ", ".join(
                    f"{f.field} ({f.description})" for f in remaining
                )
                lines.append(
                    f"Your current goal is to gather these REQUIRED fields that are still missing: "
                    f"{remaining_desc}."
                )
            if all_uncollected:
                optional_desc = ", ".join(
                    f"{f.field} ({f.description})"
                    for f in all_uncollected
                    if not f.required
                )
                if optional_desc:
                    lines.append(
                        f"These optional fields would also be valuable if they come up naturally: "
                        f"{optional_desc}."
                    )
            lines.append("")
            lines.append(
                "Ask ONE question at a time. Keep the conversation natural and flowing. "
                "Do not list all the fields — guide the conversation organically."
            )

        # --- Already collected ---
        if state.collected_fields:
            lines.append("")
            lines.append("Information already collected:")
            for field_name, value in state.collected_fields.items():
                lines.append(f"  - {field_name}: {value}")

        # --- Opening hints (first turn only) ---
        if state.turn_count == 0 and cfg.opening_hints:
            lines.append("")
            lines.append("Opening guidance:")
            for hint in cfg.opening_hints:
                lines.append(f"  - {hint}")

        # --- Pending hints from keyword triggers ---
        if state.pending_hints:
            lines.append("")
            lines.append("Important: address this in your next response:")
            for hint in state.pending_hints:
                lines.append(f"  - {hint}")

        # --- Segment info ---
        if state.detected_segment:
            lines.append("")
            lines.append(
                f"Customer segment detected: {state.detected_segment}. "
                "Tailor your questions appropriately."
            )

        # --- Max turns warning ---
        if state.turn_count >= cfg.max_turns - 2:
            lines.append("")
            lines.append(
                "The conversation is nearing its limit. Wrap up gracefully and "
                "collect any remaining critical information."
            )

        # --- Extraction instructions (appended by JsonBlockExtractor) ---
        if isinstance(self._extractor, JsonBlockExtractor):
            lines.append("")
            lines.append(self._extractor.system_prompt_addon)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Keyword triggers & segmentation
    # ------------------------------------------------------------------

    def _apply_keyword_triggers(self, state: ConversationState, message: str) -> None:
        if not self._config.keyword_triggers:
            return
        lower = message.lower()
        for keyword, trigger in self._config.keyword_triggers.items():
            if keyword.lower() in lower and keyword not in state.triggered_keywords:
                state.triggered_keywords.append(keyword)
                if trigger.action in ("note_and_probe", "probe_only") and trigger.follow_up:
                    state.pending_hints.append(trigger.follow_up)
                if trigger.action == "note_and_probe" and trigger.note_field:
                    state.collected_fields[trigger.note_field] = True
                if trigger.action == "set_field" and trigger.set_field:
                    state.collected_fields[trigger.set_field] = trigger.set_value

    def _apply_segmentation_rules(self, state: ConversationState, message: str) -> None:
        if not self._config.segmentation:
            return
        lower = message.lower()
        for rule in self._config.segmentation.rules:
            if any(kw.lower() in lower for kw in rule.if_keywords):
                if rule.set_field and rule.set_value is not None:
                    state.collected_fields[rule.set_field] = rule.set_value
                    if rule.set_field == "customer_segment":
                        state.detected_segment = rule.set_value
                if rule.follow_up:
                    state.pending_hints.append(rule.follow_up)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _remaining_required_fields(self, state: ConversationState) -> list["MetadataField"]:
        return [
            f
            for f in self._config.metadata_to_collect
            if f.required and f.field not in state.collected_fields
        ]

    def _uncollected_fields(self, state: ConversationState) -> list["MetadataField"]:
        return [
            f
            for f in self._config.metadata_to_collect
            if f.field not in state.collected_fields
        ]

    def _check_completion(self, state: ConversationState) -> bool:
        if state.turn_count >= self._config.max_turns:
            return True
        if self._config.completion.strategy == "all_required_fields_collected":
            return len(self._remaining_required_fields(state)) == 0
        return False

    def _clean_reply(self, raw: str) -> tuple[str, dict]:
        """Strip the JSON extraction block (if present) from the visible reply."""
        clean, extracted = strip_extraction_block(raw)
        return clean, extracted
