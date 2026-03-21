from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class StartInterviewResponse(BaseModel):
    session_id: str
    message: str
    collected_fields: dict[str, Any]


class TurnRequest(BaseModel):
    message: str


class TurnResponse(BaseModel):
    message: str
    collected_fields: dict[str, Any]
    is_complete: bool
    turn_count: int


class SubmitInterviewResponse(BaseModel):
    project_uuid: str
    message: str
