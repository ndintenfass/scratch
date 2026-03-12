"""API request and response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------

class CreateAgentRequest(BaseModel):
    """Create an agent from an inline spec dict (parsed YAML or JSON)."""
    spec: dict[str, Any] = Field(
        ..., description="The agent spec as a parsed dict (from YAML or JSON)"
    )


class CreateAgentFromPackageRequest(BaseModel):
    """Create an agent by pointing at an agent package directory on disk."""
    package_path: str = Field(
        ...,
        description=(
            "Absolute or relative path to an agent package directory. "
            "The directory must contain an agent.yaml file."
        ),
    )


class AgentResponse(BaseModel):
    """Returned when an agent is created or retrieved."""
    agent_id: str
    name: str
    type: str
    status: Literal["active", "deleted"]
    created_at: datetime
    llm_cloud: Optional[str] = None
    description: str = ""


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class ConversationRequest(BaseModel):
    """Submit a message to an agent and receive a retrieval token."""
    message: str = Field(..., description="The user's message to the agent")
    conversation_id: Optional[str] = Field(
        default=None,
        description=(
            "Continue an existing conversation by providing its ID. "
            "Omit to start a new conversation."
        ),
    )


class ConversationTokenResponse(BaseModel):
    """Returned immediately after submitting a message. Use the token to poll for the result."""
    token: str = Field(..., description="Retrieval token — use this to poll for the result")
    conversation_id: str
    agent_id: str
    status: Literal["pending"] = "pending"


class ConversationResult(BaseModel):
    """Polled result for a submitted conversation turn."""
    token: str
    status: Literal["pending", "processing", "complete", "error"]
    conversation_id: str
    agent_id: str
    # Populated when status == "complete"
    agent_response: Optional[str] = None
    collected_metadata: Optional[dict[str, Any]] = None
    current_segment: Optional[str] = None
    triggered_keywords: Optional[list[str]] = None
    is_complete: bool = False
    turn_count: int = 0
    # Populated when status == "error"
    error: Optional[str] = None
