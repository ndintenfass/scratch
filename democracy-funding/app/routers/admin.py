from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.project import Project
from app.models.billionaire import BillionaireUser, FundingPledge
from app.schemas.project import ProjectStatusUpdate
from app.schemas.billionaire import CreateBillionaireRequest, CreateBillionaireResponse
from app.services import project_service, billionaire_service

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBasic()


def _require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    settings = get_settings()
    ok_user = secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Invalid credentials",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


@router.get("/projects")
async def list_all_projects(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    projects = await project_service.list_projects(db, status=status, limit=limit, offset=offset)
    return [
        {
            "uuid": p.uuid,
            "title": p.title,
            "status": p.status,
            "vote_count": p.vote_count,
            "milestone_hit": p.milestone_hit,
            "outreach_triggered": p.outreach_triggered,
            "submitter_name": p.submitter_name,
            "submitter_email": p.submitter_email,
            "estimated_budget": p.estimated_budget,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@router.patch("/projects/{uuid}/status")
async def update_project_status(
    uuid: str,
    body: ProjectStatusUpdate,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    valid = {"pending", "approved", "viable", "funded", "rejected"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    project = await project_service.update_project_status(uuid, body.status, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"uuid": project.uuid, "status": project.status}


@router.patch("/projects/{uuid}/outreach")
async def trigger_outreach(
    uuid: str,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.get_project(uuid, db)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project.outreach_triggered = True
    await db.commit()
    return {"uuid": project.uuid, "outreach_triggered": True}


@router.get("/billionaires")
async def list_billionaires(
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BillionaireUser).order_by(BillionaireUser.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "alias": u.alias,
            "access_code": u.access_code,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
        }
        for u in users
    ]


@router.post("/billionaires", response_model=CreateBillionaireResponse)
async def create_billionaire(
    body: CreateBillionaireRequest,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await billionaire_service.create_billionaire_user(body.alias, db)
    return CreateBillionaireResponse(
        access_code=user.access_code,
        alias=user.alias,
        message="Access code created. Share it securely with the donor.",
    )


@router.patch("/billionaires/{user_id}/deactivate")
async def deactivate_billionaire(
    user_id: int,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BillionaireUser).where(BillionaireUser.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"id": user_id, "is_active": False}


@router.get("/pledges")
async def list_all_pledges(
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FundingPledge).order_by(FundingPledge.pledged_at.desc()))
    pledges = result.scalars().all()
    out = []
    for pledge in pledges:
        proj = await project_service.get_project_by_id(pledge.project_id, db)
        out.append({
            "id": pledge.id,
            "project_title": proj.title if proj else "Unknown",
            "project_uuid": proj.uuid if proj else None,
            "amount_usd": pledge.amount_usd,
            "status": pledge.status,
            "pledged_at": pledge.pledged_at.isoformat(),
            "milestone_verified": pledge.milestone_verified,
        })
    return out


@router.patch("/pledges/{pledge_id}/status")
async def update_pledge_status(
    pledge_id: int,
    status: str,
    _=Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    valid = {"pledged", "in_escrow", "released", "withdrawn"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    pledge = await billionaire_service.update_pledge_status(pledge_id, status, db)
    if pledge is None:
        raise HTTPException(status_code=404, detail="Pledge not found")
    return {"id": pledge.id, "status": pledge.status}
