from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.interview import (
    StartInterviewResponse,
    TurnRequest,
    TurnResponse,
    SubmitInterviewResponse,
)
from app.services import interview_service, project_service

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(db: AsyncSession = Depends(get_db)):
    session_id, opening, fields = await interview_service.start_session(db)
    return StartInterviewResponse(session_id=session_id, message=opening, collected_fields=fields)


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def interview_turn(session_id: str, body: TurnRequest, db: AsyncSession = Depends(get_db)):
    try:
        reply, fields, is_complete, turn_count = await interview_service.process_turn(
            session_id, body.message, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TurnResponse(message=reply, collected_fields=fields, is_complete=is_complete, turn_count=turn_count)


@router.post("/{session_id}/submit", response_model=SubmitInterviewResponse)
async def submit_interview(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await interview_service.get_session(session_id, db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.project_id is not None:
        # Already submitted — return existing project
        from app.models.project import Project
        from sqlalchemy import select
        result = await db.execute(select(Project).where(Project.id == session.project_id))
        p = result.scalar_one_or_none()
        if p:
            return SubmitInterviewResponse(project_uuid=p.uuid, message="Project already submitted")
    try:
        project = await project_service.create_project_from_session(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SubmitInterviewResponse(
        project_uuid=project.uuid,
        message="Your project idea has been submitted for community review!",
    )
