from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.admin import InterviewSession


async def create_project_from_session(session_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(InterviewSession).where(InterviewSession.session_id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise ValueError("Session not found")

    fields = json.loads(session.collected_fields)
    outcomes_raw = fields.get("measurable_outcomes", "")
    if isinstance(outcomes_raw, list):
        outcomes_json = json.dumps(outcomes_raw)
    else:
        outcomes_json = json.dumps([outcomes_raw]) if outcomes_raw else "[]"

    budget = fields.get("estimated_budget")
    if isinstance(budget, str):
        import re
        nums = re.findall(r"[\d,]+", budget.replace(",", ""))
        budget = float(nums[0]) if nums else None
    elif budget is not None:
        budget = float(budget)

    project = Project(
        title=fields.get("title", "Untitled Project"),
        description=fields.get("solution", ""),
        problem_statement=fields.get("problem_statement", ""),
        solution=fields.get("solution", ""),
        estimated_budget=budget,
        measurable_outcomes=outcomes_json,
        submitter_name=fields.get("submitter_name"),
        submitter_email=fields.get("submitter_email"),
        interview_session_id=session_id,
        status="pending",
    )
    db.add(project)
    session.status = "complete"

    await db.flush()
    session.project_id = project.id
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    q = select(Project).order_by(Project.vote_count.desc())
    if status:
        q = q.where(Project.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_project(uuid: str, db: AsyncSession) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.uuid == uuid))
    return result.scalar_one_or_none()


async def get_project_by_id(project_id: int, db: AsyncSession) -> Optional[Project]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def update_project_status(uuid: str, status: str, db: AsyncSession) -> Optional[Project]:
    project = await get_project(uuid, db)
    if project is None:
        return None
    project.status = status
    await db.commit()
    await db.refresh(project)
    return project
