"""Workspace management API — register bots, manage members."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Workspace, WorkspaceMember, UserRole, WorkspaceType
from app.db.repositories import WorkspaceRepository, UserRepository
from app.bots.manager import bot_manager

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    type: WorkspaceType = WorkspaceType.CUSTOM
    telegram_bot_token: str
    owner_telegram_id: int


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    type: str
    telegram_bot_username: str | None

    model_config = {"from_attributes": True}


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    body: CreateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
):
    ws_repo = WorkspaceRepository(db)
    user_repo = UserRepository(db)

    # Check token not already registered
    existing = await ws_repo.get_by_bot_token(body.telegram_bot_token)
    if existing:
        raise HTTPException(400, "Bot token already registered")

    # Register bot with manager
    bot = await bot_manager.register_bot(body.telegram_bot_token, "temp")
    bot_info = await bot.get_me()

    # Create workspace
    workspace = Workspace(
        name=body.name,
        type=body.type,
        telegram_bot_token=body.telegram_bot_token,
        telegram_bot_username=bot_info.username,
    )
    await ws_repo.save(workspace)

    # Update bot manager with real workspace id
    bot_manager._bots[body.telegram_bot_token][1]["workspace_id"] = str(workspace.id)

    # Set webhook
    webhook_url = f"{settings.webhook_base_url}/webhook/{body.telegram_bot_token}"
    await bot_manager.set_webhook(
        body.telegram_bot_token, webhook_url, settings.webhook_secret
    )

    # Add owner
    user, _ = await user_repo.get_or_create(
        telegram_id=body.owner_telegram_id,
        first_name="Owner",
    )
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=UserRole.OWNER,
    )
    db.add(member)
    await db.commit()
    await db.refresh(workspace)

    return workspace


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Workspace).where(Workspace.is_active == True))
    return list(result.scalars().all())


class MemberResponse(BaseModel):
    id: str
    role: str
    user: dict

    model_config = {"from_attributes": True}


@router.get("/{workspace_id}/members")
async def get_workspace_members(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import User

    result = await db.execute(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role.value,
            "user": {
                "id": str(m.user.id),
                "first_name": m.user.first_name,
                "last_name": m.user.last_name,
                "telegram_username": m.user.telegram_username,
            },
        }
        for m in members
    ]
