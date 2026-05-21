"""
Mini App authentication — verifies Telegram initData, issues a JWT.

Flow:
  Frontend (TG Mini App) sends { init_data, workspace_id } →
  Backend looks up workspace's bot_token →
  Verifies initData HMAC signature with that bot_token →
  Gets-or-creates User and WorkspaceMember →
  Returns JWT the frontend uses as Bearer token.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter

from app.core.security import (
    create_access_token,
    parse_init_data_user,
    verify_telegram_init_data,
)
from app.db.models import User, UserRole, Workspace, WorkspaceMember
from app.db.repositories import UserRepository
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class TelegramAuthRequest(BaseModel):
    init_data: str
    workspace_id: UUID


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    workspace: dict


@router.post("/telegram", response_model=TelegramAuthResponse)
@limiter.limit("20/minute")
async def authenticate_telegram(
    request: Request,
    body: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Look up workspace + its bot token
    workspace = await db.get(Workspace, body.workspace_id)
    if not workspace or not workspace.is_active:
        raise HTTPException(404, "Workspace not found")

    # 2. Verify HMAC signature of initData against this workspace's bot_token
    verified = verify_telegram_init_data(body.init_data, workspace.telegram_bot_token)
    if not verified:
        raise HTTPException(401, "Invalid initData signature")

    tg_user = parse_init_data_user(verified)
    if not tg_user or "id" not in tg_user:
        raise HTTPException(400, "initData missing user info")

    # 3. Get-or-create User
    user_repo = UserRepository(db)
    user, _created = await user_repo.get_or_create(
        telegram_id=tg_user["id"],
        first_name=tg_user.get("first_name") or "—",
        last_name=tg_user.get("last_name"),
        telegram_username=tg_user.get("username"),
        language_code=tg_user.get("language_code") or "ru",
    )

    # 4. Ensure WorkspaceMember exists
    existing = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    if not existing.scalar_one_or_none():
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=UserRole.EXECUTOR,
        )
        db.add(member)

    await db.commit()
    await db.refresh(user)

    # 5. Issue JWT
    token = create_access_token(user_id=str(user.id), workspace_id=str(workspace.id))

    return TelegramAuthResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "telegram_username": user.telegram_username,
        },
        workspace={
            "id": str(workspace.id),
            "name": workspace.name,
            "type": workspace.type.value if workspace.type else None,
        },
    )
