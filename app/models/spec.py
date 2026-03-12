"""
Pydantic models for the declarative agent spec format.

The spec is intentionally self-documenting: every field carries a description
and, where relevant, a collection_hint. This design supports a future
"spec designer" tool that can guide users through authoring a new spec.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Metadata field — defines one piece of information to collect
# ---------------------------------------------------------------------------

class MetadataField(BaseModel):
    """
    Describes a single structured field the agent must collect from the user.

    The agent uses `description` and `collection_hint` to understand how and
    when to gather this information during the conversation.
    """
    field: str = Field(..., description="Snake_case identifier for this field")
    label: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="What this field captures and why it matters")
    type: Literal["text", "enum", "boolean", "integer", "float", "list"] = Field(
        default="text", description="Data type for validation and display"
    )
    options: Optional[list[str]] = Field(
        default=None,
        description="Allowed values for enum fields. Must be set when type='enum'.",
    )
    required: bool = Field(
        default=True,
        description="Whether the interview is incomplete without this field",
    )
    collection_hint: Optional[str] = Field(
        default=None,
        description=(
            "Guidance for the agent on HOW to elicit this field — "
            "e.g. 'infer from context, do not ask directly' or "
            "'ask: what is your biggest challenge?'"
        ),
    )
    # Numeric bounds (for integer/float fields)
    min_value: Optional[float] = Field(default=None, description="Minimum acceptable value")
    max_value: Optional[float] = Field(default=None, description="Maximum acceptable value")


# ---------------------------------------------------------------------------
# Keyword triggers — what to do when a user mentions a particular word
# ---------------------------------------------------------------------------

class KeywordTrigger(BaseModel):
    """
    Defines a reaction when the user's message contains a keyword.

    Actions:
      note_and_probe   — record a flag in collected_fields AND inject a follow-up hint
      set_field        — set a specific field to a fixed value
      probe_only       — inject a follow-up hint without recording anything
    """
    action: Literal["note_and_probe", "set_field", "probe_only"] = "probe_only"
    # For note_and_probe: name of a boolean flag to set in collected_fields
    note_field: Optional[str] = None
    # For note_and_probe / probe_only: hint injected into the system prompt
    follow_up: Optional[str] = None
    # For set_field: which metadata field to set and what value to give it
    set_field: Optional[str] = None
    set_value: Optional[Any] = None


# ---------------------------------------------------------------------------
# Segmentation rules — auto-classify the user based on keywords
# ---------------------------------------------------------------------------

class SegmentationRule(BaseModel):
    """
    Automatically sets a field value or triggers an action when the user's
    message contains any of the listed keywords.
    """
    if_keywords: list[str] = Field(..., description="Keywords to match (case-insensitive)")
    set_field: Optional[str] = Field(
        default=None,
        description="Field name to set when keywords are detected",
    )
    set_value: Optional[Any] = Field(
        default=None,
        description="Value to set on the field",
    )
    action: Optional[str] = Field(
        default=None,
        description="Named action to execute (e.g. 'probe_current_solution')",
    )
    follow_up: Optional[str] = Field(
        default=None,
        description="Follow-up hint to inject into the system prompt",
    )


class SegmentationConfig(BaseModel):
    rules: list[SegmentationRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Completion config — when is the interview done?
# ---------------------------------------------------------------------------

class CompletionConfig(BaseModel):
    strategy: Literal["all_required_fields_collected", "max_turns"] = (
        "all_required_fields_collected"
    )
    closing_message: str = (
        "Thank you so much — this has been incredibly helpful! We'll be in touch soon."
    )


# ---------------------------------------------------------------------------
# Extraction config — how to pull structured data from the conversation
# ---------------------------------------------------------------------------

class ExtractionConfig(BaseModel):
    """
    Configures how the agent extracts structured field values from
    the freeform conversation.

    Strategies:
      json_block    (default) — the LLM appends a ```json {"extracted": {...}}```
                                block to its reply; the server strips and parses it.
      second_pass             — after the main reply, a second LLM call extracts fields.
                                More reliable but doubles LLM calls per turn.
      heuristic               — regex/keyword pattern matching; zero extra LLM calls
                                but less accurate for freeform text.
    """
    strategy: Literal["json_block", "second_pass", "heuristic"] = "json_block"


# ---------------------------------------------------------------------------
# Interview bot config — the full configuration for a discussion/interview agent
# ---------------------------------------------------------------------------

class InterviewBotConfig(BaseModel):
    """
    Configuration for an interview_bot agent. Defines everything the agent
    needs to conduct a structured discovery conversation.
    """
    topic: str = Field(..., description="The subject or purpose of the interview")
    tone: str = Field(
        default="professional and warm",
        description=(
            "The conversational tone to adopt. Examples: "
            "'warm and curious', 'formal and concise', 'casual and friendly'"
        ),
    )
    opening_hints: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered hints about how to open the conversation. "
            "The agent uses these to generate its first message."
        ),
    )
    closing_hints: list[str] = Field(
        default_factory=list,
        description="Hints about how to close the conversation gracefully.",
    )
    metadata_to_collect: list[MetadataField] = Field(
        ...,
        description="Ordered list of structured fields to gather from the user",
    )
    segmentation: Optional[SegmentationConfig] = Field(
        default=None,
        description="Rules for auto-classifying the user based on their responses",
    )
    keyword_triggers: dict[str, KeywordTrigger] = Field(
        default_factory=dict,
        description=(
            "Map of keyword → action. When the user mentions a keyword "
            "the corresponding action is triggered."
        ),
    )
    completion: CompletionConfig = Field(default_factory=CompletionConfig)
    max_turns: int = Field(
        default=20,
        description="Hard cap on conversation length regardless of completion strategy",
    )
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)


# ---------------------------------------------------------------------------
# Top-level agent spec
# ---------------------------------------------------------------------------

class AgentSpec(BaseModel):
    """
    The complete declarative definition of an agent.

    This is the root model for an agent.yaml package file or an inline spec
    submitted via the API. Every field is designed to be self-documenting so
    that a 'spec designer' tool can guide users through authoring a new spec.
    """
    name: str = Field(..., description="Human-readable name for this agent")
    description: str = Field(
        default="",
        description="What this agent does and who it is designed for",
    )
    type: Literal["interview_bot"] = Field(
        ...,
        description=(
            "Agent type — determines which implementation class is instantiated. "
            "Current supported types: interview_bot"
        ),
    )
    llm_cloud: Optional[str] = Field(
        default=None,
        description=(
            "Key referencing an entry in admin_config.yaml llm_clouds. "
            "If omitted, the admin config default is used."
        ),
    )
    config: InterviewBotConfig = Field(
        ...,
        description="Agent-type-specific configuration block",
    )
