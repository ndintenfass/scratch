from __future__ import annotations

import secrets
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _access_code() -> str:
    return f"bf_{secrets.token_urlsafe(32)}"


class BillionaireUser(Base):
    __tablename__ = "billionaire_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    access_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=_access_code)
    alias: Mapped[str] = mapped_column(String(100), nullable=False, default="Anonymous Donor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FundingPledge(Base):
    __tablename__ = "funding_pledges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    billionaire_id: Mapped[int] = mapped_column(Integer, ForeignKey("billionaire_users.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    # Amount in USD (float for prototype)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pledged | in_escrow | released | withdrawn
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pledged")
    pledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    escrow_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    milestone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
