from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.vote import VoteRequest, VoteRequestResponse, VoteConfirmResponse
from app.services import voting_service

router = APIRouter(prefix="/api/vote", tags=["voting"])


@router.post("/request", response_model=VoteRequestResponse)
async def request_vote(body: VoteRequest, db: AsyncSession = Depends(get_db)):
    try:
        token, confirm_url = await voting_service.request_vote_token(
            email=body.email,
            project_uuid=body.project_uuid,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return VoteRequestResponse(
        message="Vote token created. In production, this would be emailed to you. "
                "For this prototype, use the token/URL below to confirm your vote.",
        token=token,
        confirm_url=confirm_url,
    )


@router.get("/confirm/{token}", response_model=VoteConfirmResponse)
async def confirm_vote(token: str, db: AsyncSession = Depends(get_db)):
    try:
        project_uuid, vote_count, milestone_hit = await voting_service.confirm_vote(token, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    msg = "Your vote has been recorded!"
    if milestone_hit:
        msg += " 🎉 This project has reached 1,000,000 votes! We will now work to bring it to the attention of potential funders."
    return VoteConfirmResponse(
        message=msg,
        project_uuid=project_uuid,
        new_vote_count=vote_count,
        milestone_hit=milestone_hit,
    )
