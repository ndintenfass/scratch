"""
Agent factory — creates a live agent from a parsed spec + admin config.

Adding a new agent type:
  1. Create a class in app/agents/ that inherits BaseAgent
  2. Add a branch in AgentFactory.create() dispatching on spec.type
  3. Register the new Literal type in AgentSpec.type (models/spec.py)
"""
from __future__ import annotations

import uuid

from app.models.admin import AdminConfig
from app.models.spec import AgentSpec
from app.llm import get_proxy
from .base import BaseAgent
from .interview_bot import InterviewBotAgent


class AgentFactory:
    def __init__(self, admin_config: AdminConfig) -> None:
        self._admin_config = admin_config

    def create(self, spec: AgentSpec, agent_id: str | None = None) -> BaseAgent:
        """
        Instantiate the appropriate agent class for the given spec.

        Args:
            spec:     validated AgentSpec
            agent_id: optional pre-assigned ID; a UUID is generated if omitted

        Returns:
            A live BaseAgent subclass wired to the correct LLM proxy.
        """
        if agent_id is None:
            agent_id = f"agent_{uuid.uuid4().hex[:12]}"

        cloud_config = self._admin_config.get_cloud(spec.llm_cloud)
        llm_proxy = get_proxy(cloud_config)

        if spec.type == "interview_bot":
            return InterviewBotAgent(spec=spec, llm_proxy=llm_proxy, agent_id=agent_id)

        raise ValueError(
            f"Unknown agent type: '{spec.type}'. "
            "Supported types: interview_bot"
        )
