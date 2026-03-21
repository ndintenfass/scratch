from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import ProjectSummary, ProjectDetail
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    # Public listing shows only approved/viable/funded projects
    allowed = {"approved", "viable", "funded"}
    if status and status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    effective_status = status  # None = all public statuses
    projects = await project_service.list_projects(db, status=effective_status, limit=limit, offset=offset)
    # Filter to public-only if no status filter
    if not status:
        projects = [p for p in projects if p.status in allowed]
    return projects


@router.get("/{uuid}", response_model=ProjectDetail)
async def get_project(uuid: str, db: AsyncSession = Depends(get_db)):
    project = await project_service.get_project(uuid, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("approved", "viable", "funded"):
        raise HTTPException(status_code=404, detail="Project not found")
    return project
