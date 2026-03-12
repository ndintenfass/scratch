"""
Field extraction strategies.

Extraction is the process of pulling structured field values out of a
freeform LLM conversation response.

Available strategies (configured via spec's extraction.strategy):
  json_block   (default) — LLM appends a ```json {"extracted": {...}}``` block
  second_pass             — a second LLM call extracts fields post-response
  heuristic               — regex/keyword pattern matching, no extra LLM calls
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.spec import ExtractionConfig

from .base import ExtractionStrategy
from .json_block import JsonBlockExtractor
from .second_pass import SecondPassExtractor
from .heuristic import HeuristicExtractor


def get_extraction_strategy(config: "ExtractionConfig") -> ExtractionStrategy:
    if config.strategy == "json_block":
        return JsonBlockExtractor()
    if config.strategy == "second_pass":
        return SecondPassExtractor()
    if config.strategy == "heuristic":
        return HeuristicExtractor()
    raise ValueError(f"Unknown extraction strategy: {config.strategy}")


__all__ = [
    "ExtractionStrategy",
    "get_extraction_strategy",
    "JsonBlockExtractor",
    "SecondPassExtractor",
    "HeuristicExtractor",
]
