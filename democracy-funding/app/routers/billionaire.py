from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.billionaire import (
    BillionaireLoginRequest,
    BillionaireLoginResponse,
    PledgeRequest,
    PledgeResponse,
)
from app.services import billionaire_service
from app.schemas.project import ProjectSummary

router = APIRouter(prefix="/api/billionaire", tags=["billionaire"])


async def _require_billionaire(
    access_code: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not access_code:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await billionaire_service.authenticate(access_code, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or inactive access code")
    return user


@router.post("/login", response_model=BillionaireLoginResponse)
async def login(
    body: BillionaireLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await billionaire_service.authenticate(body.access_code, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access code")
    response.set_cookie(
        key="access_code",
        value=body.access_code,
        httponly=True,
        samesite="strict",
        max_age=86400 * 7,
    )
    return BillionaireLoginResponse(message="Welcome to the private portal.", alias=user.alias)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_code")
    return {"message": "Logged out"}


@router.get("/projects", response_model=list[ProjectSummary])
async def list_fundable_projects(
    user=Depends(_require_billionaire),
    db: AsyncSession = Depends(get_db),
):
    return await billionaire_service.list_fundable_projects(db)


@router.post("/pledge", response_model=PledgeResponse)
async def create_pledge(
    body: PledgeRequest,
    user=Depends(_require_billionaire),
    db: AsyncSession = Depends(get_db),
):
    try:
        pledge, project = await billionaire_service.create_pledge(
            billionaire_id=user.id,
            project_uuid=body.project_uuid,
            amount_usd=body.amount_usd,
            notes=body.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PledgeResponse(
        id=pledge.id,
        project_uuid=project.uuid,
        project_title=project.title,
        amount_usd=pledge.amount_usd,
        status=pledge.status,
        pledged_at=pledge.pledged_at,
    )


@router.get("/pledges")
async def my_pledges(
    user=Depends(_require_billionaire),
    db: AsyncSession = Depends(get_db),
):
    pairs = await billionaire_service.list_pledges_for_user(user.id, db)
    return [
        {
            "id": pledge.id,
            "project_uuid": project.uuid,
            "project_title": project.title,
            "amount_usd": pledge.amount_usd,
            "status": pledge.status,
            "pledged_at": pledge.pledged_at.isoformat(),
        }
        for pledge, project in pairs
    ]
