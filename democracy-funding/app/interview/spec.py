from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel


class MetadataField(BaseModel):
    field: str
    label: str
    description: str
    type: str = "text"
    options: list[str] = []
    required: bool = True
    collection_hint: str = ""


class CompletionConfig(BaseModel):
    strategy: str = "all_required_fields_collected"
    closing_message: str = "Thank you for sharing your idea!"


class ExtractionConfig(BaseModel):
    strategy: str = "json_block"


class InterviewBotConfig(BaseModel):
    topic: str
    tone: str = "warm and curious"
    opening_hints: list[str] = []
    closing_hints: list[str] = []
    metadata_to_collect: list[MetadataField] = []
    completion: CompletionConfig = CompletionConfig()
    extraction: ExtractionConfig = ExtractionConfig()
    max_turns: int = 25
