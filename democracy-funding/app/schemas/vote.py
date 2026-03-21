from __future__ import annotations

from pydantic import BaseModel, EmailStr


class VoteRequest(BaseModel):
    email: str
    project_uuid: str


class VoteRequestResponse(BaseModel):
    message: str
    # In prototype mode the token is returned directly; in production it's emailed
    token: str
    confirm_url: str


class VoteConfirmResponse(BaseModel):
    message: str
    project_uuid: str
    new_vote_count: int
    milestone_hit: bool
