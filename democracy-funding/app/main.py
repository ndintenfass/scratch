from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db
from app.routers import interview, projects, voting, billionaire, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Democracy Funding Platform",
    description="A platform for crowdsourcing and funding democracy-saving projects.",
    version="0.1.0",
    lifespan=lifespan,
)

# API routes
app.include_router(interview.router)
app.include_router(projects.router)
app.include_router(voting.router)
app.include_router(billionaire.router)
app.include_router(admin.router)

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# SPA-style page routes
@app.get("/")
async def index():
    return FileResponse(static_dir / "index.html")


@app.get("/interview")
async def interview_page():
    return FileResponse(static_dir / "interview.html")


@app.get("/project/{uuid}")
async def project_page(uuid: str):
    return FileResponse(static_dir / "project.html")


@app.get("/billionaire-portal")
async def billionaire_portal():
    return FileResponse(static_dir / "billionaire.html")


@app.get("/admin-dashboard")
async def admin_dashboard():
    return FileResponse(static_dir / "admin.html")
