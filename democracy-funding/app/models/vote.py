from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token() -> str:
    return f"vtok_{secrets.token_hex(24)}"


def _expires() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


class VoteToken(Base):
    __tablename__ = "vote_tokens"
    __table_args__ = (
        UniqueConstraint("email", "project_id", name="uq_vote_token_email_project"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=_token)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    # pending | used | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_expires)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("email", "project_id", name="uq_vote_email_project"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    token_id: Mapped[int] = mapped_column(Integer, ForeignKey("vote_tokens.id"), nullable=False)
    cast_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
