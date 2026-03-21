from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectSummary(BaseModel):
    uuid: str
    title: str
    description: str
    status: str
    vote_count: int
    milestone_hit: bool
    estimated_budget: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    uuid: str
    title: str
    description: str
    problem_statement: str
    solution: str
    estimated_budget: Optional[float]
    measurable_outcomes: str  # JSON array string
    submitter_name: Optional[str]
    status: str
    vote_count: int
    milestone_hit: bool
    outreach_triggered: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectStatusUpdate(BaseModel):
    status: str  # pending | approved | viable | funded | rejected
