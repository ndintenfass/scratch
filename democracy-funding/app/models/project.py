from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_hex() -> str:
    return _uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default=_uuid_hex)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON array stored as text: ["outcome1", "outcome2", ...]
    measurable_outcomes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    submitter_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submitter_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # pending | approved | viable | funded | rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestone_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    milestone_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outreach_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interview_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
