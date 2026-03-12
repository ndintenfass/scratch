"""
FastAPI routes for the Declarative Agent Framework API.

Routes:
  POST   /agents                              Create agent from inline spec
  POST   /agents/from-package                 Create agent from package directory
  GET    /agents/{agent_id}                   Describe an agent
  DELETE /agents/{agent_id}                   Deactivate an agent
  POST   /agents/{agent_id}/conversations     Submit a message, get a retrieval token
  GET    /agents/{agent_id}/conversations/{token}  Poll for result
  GET    /health                              Liveness check
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import ValidationError

from app.agents.base import ConversationState
from app.models.api import (
    AgentResponse,
    ConversationRequest,
    ConversationResult,
    ConversationTokenResponse,
    CreateAgentFromPackageRequest,
    CreateAgentRequest,
)
from app.models.spec import AgentSpec
from app.store import AgentStore

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_store(request: Request) -> AgentStore:
    return request.app.state.store


def _get_factory(request: Request):
    return request.app.state.factory


async def _create_agent_from_spec(
    raw_spec: dict[str, Any],
    store: AgentStore,
    factory,
) -> AgentResponse:
    """Shared logic for both inline and package-based agent creation."""
    try:
        spec = AgentSpec.model_validate(raw_spec)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    agent = factory.create(spec)
    record = await store.create_agent(agent, spec)

    return AgentResponse(
        agent_id=record.agent_id,
        name=spec.name,
        type=spec.type,
        status=record.status,
        created_at=record.created_at,
        llm_cloud=spec.llm_cloud,
        description=spec.description,
    )


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------

@router.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(body: CreateAgentRequest, request: Request):
    """Create a live agent from an inline spec (parsed YAML/JSON dict)."""
    return await _create_agent_from_spec(
        body.spec,
        _get_store(request),
        _get_factory(request),
    )


@router.post("/agents/from-package", response_model=AgentResponse, status_code=201)
async def create_agent_from_package(body: CreateAgentFromPackageRequest, request: Request):
    """
    Create a live agent by pointing at an agent package directory.
    The directory must contain an agent.yaml file.
    """
    import pathlib

    pkg_path = pathlib.Path(body.package_path)
    agent_yaml_path = pkg_path / "agent.yaml"

    if not agent_yaml_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No agent.yaml found in package directory: {pkg_path.resolve()}",
        )

    with agent_yaml_path.open() as f:
        raw_spec = yaml.safe_load(f)

    return await _create_agent_from_spec(
        raw_spec,
        _get_store(request),
        _get_factory(request),
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, request: Request):
    store = _get_store(request)
    record = await store.get_agent(agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return AgentResponse(
        agent_id=record.agent_id,
        name=record.spec.name,
        type=record.spec.type,
        status=record.status,
        created_at=record.created_at,
        llm_cloud=record.spec.llm_cloud,
        description=record.spec.description,
    )


@router.delete("/agents/{agent_id}", status_code=200)
async def delete_agent(agent_id: str, request: Request):
    store = _get_store(request)
    deleted = await store.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"agent_id": agent_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# Conversations — async token pattern
# ---------------------------------------------------------------------------

@router.post(
    "/agents/{agent_id}/conversations",
    response_model=ConversationTokenResponse,
    status_code=202,
)
async def submit_message(
    agent_id: str,
    body: ConversationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Submit a message to an agent.

    Returns a retrieval token immediately. The actual LLM call runs in the
    background. Poll GET /agents/{agent_id}/conversations/{token} for the result.

    If conversation_id is omitted, a new conversation is started and the
    agent's opening message is generated. Provide conversation_id to continue.
    """
    store = _get_store(request)
    record = await store.get_agent(agent_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    if record.status == "deleted":
        raise HTTPException(status_code=410, detail=f"Agent '{agent_id}' has been deleted")

    # Resolve or create conversation state
    is_new_conversation = body.conversation_id is None
    if body.conversation_id:
        state = await store.get_conversation(body.conversation_id)
        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{body.conversation_id}' not found",
            )
    else:
        # New conversation — will be started in background task
        from app.agents.base import ConversationState
        state = ConversationState.new(agent_id)
        await store.save_conversation(state)

    token = await store.create_token(agent_id, state.conversation_id)

    background_tasks.add_task(
        _process_conversation,
        store=store,
        agent=record.agent,
        state=state,
        message=body.message,
        token=token,
        is_new_conversation=is_new_conversation,
    )

    return ConversationTokenResponse(
        token=token,
        conversation_id=state.conversation_id,
        agent_id=agent_id,
    )


async def _process_conversation(
    store: AgentStore,
    agent,
    state: ConversationState,
    message: str,
    token: str,
    is_new_conversation: bool,
) -> None:
    """Background task: run one conversation turn and store the result."""
    await store.set_token_processing(token)
    try:
        if is_new_conversation:
            # Generate opening message first, then process the user's initial message
            opening, state = await agent.start_conversation()
            await store.save_conversation(state)

        agent_reply, updated_state = await agent.process_message(state, message)
        await store.save_conversation(updated_state)

        result = ConversationResult(
            token=token,
            status="complete",
            conversation_id=updated_state.conversation_id,
            agent_id=updated_state.agent_id,
            agent_response=agent_reply,
            collected_metadata=updated_state.collected_fields,
            current_segment=updated_state.detected_segment,
            triggered_keywords=updated_state.triggered_keywords,
            is_complete=updated_state.is_complete,
            turn_count=updated_state.turn_count,
        )
    except Exception as exc:
        result = ConversationResult(
            token=token,
            status="error",
            conversation_id=state.conversation_id,
            agent_id=state.agent_id,
            error=str(exc),
        )

    await store.set_token_result(token, result)


@router.get(
    "/agents/{agent_id}/conversations/{token}",
    response_model=ConversationResult,
)
async def get_conversation_result(agent_id: str, token: str, request: Request):
    """
    Poll for the result of a submitted conversation turn.

    status values:
      pending    — queued, not yet started
      processing — LLM call in progress
      complete   — result available
      error      — something went wrong (see `error` field)
    """
    store = _get_store(request)
    token_record = await store.get_token(token)

    if token_record is None:
        raise HTTPException(status_code=404, detail=f"Token '{token}' not found")
    if token_record.agent_id != agent_id:
        raise HTTPException(status_code=404, detail=f"Token '{token}' not found for agent '{agent_id}'")

    if token_record.status in ("pending", "processing"):
        return ConversationResult(
            token=token,
            status=token_record.status,  # type: ignore[arg-type]
            conversation_id=token_record.conversation_id,
            agent_id=agent_id,
        )

    return token_record.result


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {"status": "ok", "service": "declarative-agent-framework"}
