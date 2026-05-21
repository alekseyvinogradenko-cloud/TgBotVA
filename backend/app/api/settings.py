"""User settings API — TMA-authed. Mirrors the bot's /settings."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TmaSession, get_tma_session
from app.db.models import User
from app.db.session import get_db
from app.services.ai_service import CLAUDE_MODELS

router = APIRouter(prefix="/settings", tags=["settings"])

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class SettingsResponse(BaseModel):
    notify_morning_digest: bool
    notify_morning_time: str
    notify_weekly_report: bool
    timezone: str
    ai_model: str

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    notify_morning_digest: Optional[bool] = None
    notify_morning_time: Optional[str] = None
    notify_weekly_report: Optional[bool] = None
    timezone: Optional[str] = None
    ai_model: Optional[str] = None


def _serialize(u: User) -> SettingsResponse:
    return SettingsResponse(
        notify_morning_digest=bool(u.notify_morning_digest),
        notify_morning_time=u.notify_morning_time or "09:00",
        notify_weekly_report=bool(u.notify_weekly_report),
        timezone=u.timezone or "Europe/Moscow",
        ai_model=u.ai_model or "claude-sonnet-4-6",
    )


@router.get("", response_model=SettingsResponse)
async def get_settings(session: TmaSession = Depends(get_tma_session)):
    return _serialize(session.user)


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, session.user.id)
    if not user:
        raise HTTPException(404, "User not found")

    data = body.model_dump(exclude_unset=True)

    if "notify_morning_digest" in data:
        user.notify_morning_digest = data["notify_morning_digest"]
    if "notify_weekly_report" in data:
        user.notify_weekly_report = data["notify_weekly_report"]
    if "notify_morning_time" in data and data["notify_morning_time"]:
        t = data["notify_morning_time"]
        if not _TIME_RE.match(t):
            raise HTTPException(400, "Время в формате HH:MM")
        user.notify_morning_time = t
    if "timezone" in data and data["timezone"]:
        tz = data["timezone"]
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(tz)
        except Exception:
            raise HTTPException(400, f"Неизвестный часовой пояс: {tz}")
        user.timezone = tz
    if "ai_model" in data and data["ai_model"]:
        if data["ai_model"] not in CLAUDE_MODELS:
            raise HTTPException(400, "Неизвестная модель")
        user.ai_model = data["ai_model"]

    await db.commit()
    await db.refresh(user)
    return _serialize(user)
