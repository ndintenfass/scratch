from __future__ import annotations

import json
import secrets
import uuid
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interview.bot import InterviewBot
from app.interview.spec import InterviewBotConfig
from app.models.admin import InterviewSession
from app.services.llm_factory import build_llm_proxy


_SPEC_PATH = Path(__file__).parent.parent.parent / "specs" / "idea_collector.yaml"
_bot: InterviewBot | None = None


def _get_bot() -> InterviewBot:
    global _bot
    if _bot is None:
        raw = yaml.safe_load(_SPEC_PATH.read_text())
        config = InterviewBotConfig.model_validate(raw)
        llm = build_llm_proxy()
        _bot = InterviewBot(config=config, llm_proxy=llm)
    return _bot


async def start_session(db: AsyncSession) -> tuple[str, str, dict]:
    bot = _get_bot()
    opening, history, fields = await bot.start()
    session_id = f"sess_{uuid.uuid4().hex[:16]}"
    session = InterviewSession(
        session_id=session_id,
        conversation_history=json.dumps(history),
        collected_fields=json.dumps(fields),
        turn_count=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session_id, opening, fields


async def process_turn(
    session_id: str,
    user_message: str,
    db: AsyncSession,
) -> tuple[str, dict[str, Any], bool, int]:
    result = await db.execute(select(InterviewSession).where(InterviewSession.session_id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise ValueError("Session not found")
    if session.status != "active":
        raise ValueError("Session is not active")

    bot = _get_bot()
    history = json.loads(session.conversation_history)
    fields = json.loads(session.collected_fields)

    reply, updated_history, updated_fields, is_complete = await bot.turn(
        user_message=user_message,
        history_raw=history,
        fields=fields,
        turn_count=session.turn_count,
    )

    session.conversation_history = json.dumps(updated_history)
    session.collected_fields = json.dumps(updated_fields)
    session.turn_count = session.turn_count + 1
    session.is_complete = is_complete
    if is_complete:
        session.status = "complete"

    await db.commit()
    return reply, updated_fields, is_complete, session.turn_count


async def get_session(session_id: str, db: AsyncSession) -> InterviewSession | None:
    result = await db.execute(select(InterviewSession).where(InterviewSession.session_id == session_id))
    return result.scalar_one_or_none()
