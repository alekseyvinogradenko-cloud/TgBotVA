"""Workspace management API — register bots, manage members."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import TmaSession, get_tma_session
from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, Workspace, WorkspaceMember, UserRole, WorkspaceType
from app.db.repositories import WorkspaceRepository, UserRepository
from app.bots.manager import bot_manager, webhook_id_for

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ─── TMA: members of caller's workspace (for assignee picker) ──────────────────

class MemberItem(BaseModel):
    id: UUID
    first_name: str
    initials: str
    role: str
    is_me: bool


@router.get("/members", response_model=list[MemberItem])
async def get_my_workspace_members(
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == session.workspace_id)
    )
    members = result.scalars().all()
    items: list[MemberItem] = []
    for m in members:
        u = m.user
        if not u:
            continue
        f = (u.first_name or "").strip()
        l = (u.last_name or "").strip()
        initials = (f[:1] + (l[:1] if l else "")).upper() or "—"
        items.append(
            MemberItem(
                id=u.id,
                first_name=u.first_name,
                initials=initials,
                role=m.role.value if m.role else "executor",
                is_me=(u.id == session.user.id),
            )
        )
    # Caller first, then alphabetical
    items.sort(key=lambda x: (not x.is_me, x.first_name.lower()))
    return items


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


import hmac as _hmac
from fastapi import Header


def _require_admin(x_admin_key: str = Header(None)):
    """Gate workspace registration behind a server-side admin key.
    If ADMIN_API_KEY is unset, the endpoint is disabled entirely (403)."""
    if not settings.admin_api_key:
        raise HTTPException(403, "Workspace registration disabled")
    if not x_admin_key or not _hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(403, "Invalid admin key")


@router.post("/", response_model=WorkspaceResponse, dependencies=[Depends(_require_admin)])
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

    # Set webhook (opaque id, not the raw token)
    webhook_url = f"{settings.webhook_base_url}/webhook/{webhook_id_for(body.telegram_bot_token)}"
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
async def list_workspaces(
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    """Return only workspaces the caller is a member of."""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == session.user.id)
        .where(Workspace.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


# Note: the public GET /{workspace_id}/members endpoint was removed (leaked PII
# of any workspace by UUID). The Mini App uses the TMA-authed GET /members above,
# which scopes to the caller's own workspace.
