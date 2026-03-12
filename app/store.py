"""
In-memory store for agents, conversations, and retrieval tokens.

This is intentionally simple — all state lives in Python dicts.
For production, replace the backing store with Redis or Postgres while
keeping the same async interface; no other code needs to change.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.base import BaseAgent, ConversationState
    from app.models.api import ConversationResult
    from app.models.spec import AgentSpec


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentRecord:
    """Metadata about a live agent instance."""
    agent_id: str
    agent: "BaseAgent"
    spec: "AgentSpec"
    status: Literal["active", "deleted"] = "active"
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class TokenRecord:
    """Tracks the status and result of one submitted conversation turn."""
    token: str
    agent_id: str
    conversation_id: str
    status: Literal["pending", "processing", "complete", "error"] = "pending"
    result: Optional["ConversationResult"] = None


class AgentStore:
    """Thread-safe (asyncio) in-memory store."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._conversations: dict[str, "ConversationState"] = {}
        self._tokens: dict[str, TokenRecord] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    async def create_agent(self, agent: "BaseAgent", spec: "AgentSpec") -> AgentRecord:
        record = AgentRecord(agent_id=agent.agent_id, agent=agent, spec=spec)
        async with self._lock:
            self._agents[agent.agent_id] = record
        return record

    async def get_agent(self, agent_id: str) -> Optional[AgentRecord]:
        return self._agents.get(agent_id)

    async def delete_agent(self, agent_id: str) -> bool:
        async with self._lock:
            record = self._agents.get(agent_id)
            if record is None:
                return False
            record.status = "deleted"
        return True

    async def list_agents(self) -> list[AgentRecord]:
        return list(self._agents.values())

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    async def save_conversation(self, state: "ConversationState") -> None:
        async with self._lock:
            self._conversations[state.conversation_id] = state

    async def get_conversation(self, conversation_id: str) -> Optional["ConversationState"]:
        return self._conversations.get(conversation_id)

    # ------------------------------------------------------------------
    # Tokens
    # ------------------------------------------------------------------

    async def create_token(self, agent_id: str, conversation_id: str) -> str:
        token = f"tok_{uuid.uuid4().hex}"
        record = TokenRecord(
            token=token,
            agent_id=agent_id,
            conversation_id=conversation_id,
        )
        async with self._lock:
            self._tokens[token] = record
        return token

    async def set_token_processing(self, token: str) -> None:
        async with self._lock:
            record = self._tokens.get(token)
            if record:
                record.status = "processing"

    async def set_token_result(self, token: str, result: "ConversationResult") -> None:
        async with self._lock:
            record = self._tokens.get(token)
            if record:
                record.status = result.status  # type: ignore[assignment]
                record.result = result

    async def get_token(self, token: str) -> Optional[TokenRecord]:
        return self._tokens.get(token)
