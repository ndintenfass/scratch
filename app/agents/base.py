"""
Abstract base class for all agent types.

Each agent type (interview_bot, etc.) inherits from BaseAgent and implements
two methods:
  start_conversation() — initialise state, generate opening message
  process_message()    — handle one user turn, return reply + updated state
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
import uuid

if TYPE_CHECKING:
    from app.llm.base import BaseLLMProxy, LLMMessage
    from app.models.spec import AgentSpec


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ConversationState:
    """
    Holds the full mutable state of a single conversation.

    This object is stored in the AgentStore and updated after every turn.
    For production, this dataclass maps directly to a persistence schema
    (e.g. a Redis hash or a Postgres JSONB column).
    """
    conversation_id: str
    agent_id: str
    # Full message history (user + assistant turns)
    history: list["LLMMessage"] = field(default_factory=list)
    # Structured fields collected so far
    collected_fields: dict[str, Any] = field(default_factory=dict)
    # Interview complete?
    is_complete: bool = False
    # Conversation turn counter (each user message = one turn)
    turn_count: int = 0
    # Current segment inferred from responses
    detected_segment: Optional[str] = None
    # Keywords that have been detected and acted on
    triggered_keywords: list[str] = field(default_factory=list)
    # Pending follow-up hints to inject into the next system prompt
    pending_hints: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def new(cls, agent_id: str) -> "ConversationState":
        return cls(
            conversation_id=f"conv_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
        )

    def touch(self) -> None:
        self.updated_at = _utcnow()


class BaseAgent(ABC):
    """
    Abstract base for all agent implementations.

    Subclasses receive the parsed AgentSpec and an LLM proxy on construction.
    They implement start_conversation() and process_message() to define the
    agent's conversational behaviour.
    """

    def __init__(self, spec: "AgentSpec", llm_proxy: "BaseLLMProxy", agent_id: str) -> None:
        self.spec = spec
        self.llm_proxy = llm_proxy
        self.agent_id = agent_id

    @abstractmethod
    async def start_conversation(self) -> tuple[str, ConversationState]:
        """
        Initialise a new conversation.

        Returns:
            (opening_message, initial_state)
        """
        ...

    @abstractmethod
    async def process_message(
        self,
        state: ConversationState,
        message: str,
    ) -> tuple[str, ConversationState]:
        """
        Process one user message turn.

        Args:
            state:   current conversation state (will be mutated and returned)
            message: the user's message text

        Returns:
            (agent_reply, updated_state)
        """
        ...
