from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BillionaireLoginRequest(BaseModel):
    access_code: str


class BillionaireLoginResponse(BaseModel):
    message: str
    alias: str


class PledgeRequest(BaseModel):
    project_uuid: str
    amount_usd: float
    notes: Optional[str] = None


class PledgeResponse(BaseModel):
    id: int
    project_uuid: str
    project_title: str
    amount_usd: float
    status: str
    pledged_at: datetime

    class Config:
        from_attributes = True


class CreateBillionaireRequest(BaseModel):
    alias: str = "Anonymous Donor"


class CreateBillionaireResponse(BaseModel):
    access_code: str
    alias: str
    message: str
