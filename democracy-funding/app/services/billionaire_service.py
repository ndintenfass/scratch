from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billionaire import BillionaireUser, FundingPledge
from app.models.project import Project


async def authenticate(access_code: str, db: AsyncSession) -> Optional[BillionaireUser]:
    result = await db.execute(
        select(BillionaireUser).where(
            BillionaireUser.access_code == access_code,
            BillionaireUser.is_active == True,
        )
    )
    user = result.scalar_one_or_none()
    if user:
        user.last_seen_at = datetime.now(timezone.utc)
        await db.commit()
    return user


async def create_pledge(
    billionaire_id: int,
    project_uuid: str,
    amount_usd: float,
    notes: Optional[str],
    db: AsyncSession,
) -> tuple[FundingPledge, Project]:
    proj_result = await db.execute(select(Project).where(Project.uuid == project_uuid))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise ValueError("Project not found")
    if project.status not in ("viable", "approved"):
        raise ValueError("Project is not available for funding")

    pledge = FundingPledge(
        billionaire_id=billionaire_id,
        project_id=project.id,
        amount_usd=amount_usd,
        notes=notes,
    )
    db.add(pledge)
    await db.commit()
    await db.refresh(pledge)
    return pledge, project


async def list_pledges_for_user(billionaire_id: int, db: AsyncSession) -> list[tuple[FundingPledge, Project]]:
    result = await db.execute(
        select(FundingPledge).where(FundingPledge.billionaire_id == billionaire_id)
        .order_by(FundingPledge.pledged_at.desc())
    )
    pledges = list(result.scalars().all())
    out = []
    for pledge in pledges:
        proj_result = await db.execute(select(Project).where(Project.id == pledge.project_id))
        project = proj_result.scalar_one_or_none()
        if project:
            out.append((pledge, project))
    return out


async def list_fundable_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.status.in_(["viable", "approved"]))
        .order_by(Project.vote_count.desc())
    )
    return list(result.scalars().all())


async def create_billionaire_user(alias: str, db: AsyncSession) -> BillionaireUser:
    user = BillionaireUser(alias=alias)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_pledge_status(pledge_id: int, status: str, db: AsyncSession) -> Optional[FundingPledge]:
    result = await db.execute(select(FundingPledge).where(FundingPledge.id == pledge_id))
    pledge = result.scalar_one_or_none()
    if pledge is None:
        return None
    pledge.status = status
    now = datetime.now(timezone.utc)
    if status == "in_escrow":
        pledge.escrow_at = now
    elif status == "released":
        pledge.released_at = now
        pledge.milestone_verified = True
    await db.commit()
    await db.refresh(pledge)
    return pledge
