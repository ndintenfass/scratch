from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.vote import VoteToken, Vote
from app.models.project import Project
from app.config import get_settings


async def request_vote_token(
    email: str,
    project_uuid: str,
    db: AsyncSession,
) -> tuple[str, str]:
    """Create a vote token. Returns (token, confirm_url)."""
    result = await db.execute(select(Project).where(Project.uuid == project_uuid))
    project = result.scalar_one_or_none()
    if project is None:
        raise ValueError("Project not found")
    if project.status not in ("approved", "viable", "funded"):
        raise ValueError("Project is not open for voting")

    # Check if already voted
    vote_result = await db.execute(
        select(Vote).where(Vote.email == email.lower().strip(), Vote.project_id == project.id)
    )
    if vote_result.scalar_one_or_none():
        raise ValueError("You have already voted for this project")

    # Check for existing pending token
    token_result = await db.execute(
        select(VoteToken).where(
            VoteToken.email == email.lower().strip(),
            VoteToken.project_id == project.id,
            VoteToken.status == "pending",
        )
    )
    existing = token_result.scalar_one_or_none()
    if existing and existing.expires_at > datetime.now(timezone.utc):
        token = existing.token
    else:
        vote_token = VoteToken(
            email=email.lower().strip(),
            project_id=project.id,
        )
        db.add(vote_token)
        await db.flush()
        token = vote_token.token

    await db.commit()
    settings = get_settings()
    confirm_url = f"{settings.base_url}/api/vote/confirm/{token}"
    return token, confirm_url


async def confirm_vote(token: str, db: AsyncSession) -> tuple[str, int, bool]:
    """Confirm a vote from magic link. Returns (project_uuid, new_vote_count, milestone_hit)."""
    result = await db.execute(select(VoteToken).where(VoteToken.token == token))
    vote_token = result.scalar_one_or_none()
    if vote_token is None:
        raise ValueError("Invalid token")
    if vote_token.status == "used":
        raise ValueError("Token already used")
    if vote_token.status == "expired" or vote_token.expires_at < datetime.now(timezone.utc):
        vote_token.status = "expired"
        await db.commit()
        raise ValueError("Token expired")

    # Check duplicate vote
    dup = await db.execute(
        select(Vote).where(
            Vote.email == vote_token.email,
            Vote.project_id == vote_token.project_id,
        )
    )
    if dup.scalar_one_or_none():
        vote_token.status = "used"
        await db.commit()
        raise ValueError("Already voted")

    vote = Vote(
        email=vote_token.email,
        project_id=vote_token.project_id,
        token_id=vote_token.id,
    )
    db.add(vote)

    vote_token.status = "used"
    vote_token.used_at = datetime.now(timezone.utc)

    # Increment vote count
    proj_result = await db.execute(select(Project).where(Project.id == vote_token.project_id))
    project = proj_result.scalar_one()
    project.vote_count = project.vote_count + 1

    # Check milestone
    settings = get_settings()
    if not project.milestone_hit and project.vote_count >= settings.vote_threshold:
        project.milestone_hit = True
        project.milestone_hit_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(project)
    return project.uuid, project.vote_count, project.milestone_hit
