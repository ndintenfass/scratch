"""
FastAPI application entrypoint.

Startup:
  - Loads admin_config.yaml
  - Creates AgentStore and AgentFactory, attaches them to app.state

Run locally:
  uvicorn app.main:app --reload

Run on Render (via render.yaml):
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import load_admin_config
from app.agents.factory import AgentFactory
from app.store import AgentStore
from app.routers.agents import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -----------------------------------------------------------------------
    # Startup
    # -----------------------------------------------------------------------
    admin_config = load_admin_config()
    app.state.store = AgentStore()
    app.state.factory = AgentFactory(admin_config)
    app.state.admin_config = admin_config
    yield
    # -----------------------------------------------------------------------
    # Shutdown — nothing to clean up in the prototype
    # -----------------------------------------------------------------------


app = FastAPI(
    title="Declarative Agent Framework",
    description=(
        "Spin up fully live agents from a declarative YAML spec. "
        "Submit requests via the API, get a retrieval token, poll for the result."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
