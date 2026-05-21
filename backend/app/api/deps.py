"""
FastAPI dependencies — TMA (Telegram Mini App) Bearer auth.
"""
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import User, UserRole, WorkspaceMember
from app.db.session import get_db


class TmaSession:
    """Authenticated mini-app caller — user + workspace scope + role."""
    def __init__(self, user: User, workspace_id: UUID, role: UserRole):
        self.user = user
        self.workspace_id = workspace_id
        self.role = role


async def get_tma_session(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> TmaSession:
    """Parse `Authorization: Bearer <jwt>`, return the active TMA session.

    Re-verifies workspace membership on EVERY request (not just at token issue)
    so a removed member loses access immediately rather than at JWT expiry.
    Raises 401 on missing/invalid/expired token or revoked membership.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    payload = decode_access_token(token)
    if not payload or "sub" not in payload or "ws" not in payload:
        raise HTTPException(401, "Invalid or expired token")

    try:
        user_id = UUID(payload["sub"])
        workspace_id = UUID(payload["ws"])
    except (ValueError, TypeError):
        raise HTTPException(401, "Malformed token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    # Membership re-check — revocation takes effect immediately
    result = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(401, "Membership revoked")

    return TmaSession(user=user, workspace_id=workspace_id, role=member.role)


def require_role(*allowed: UserRole):
    """Dependency factory — gate an endpoint behind workspace roles.

    Usage: session: TmaSession = Depends(require_role(UserRole.OWNER, UserRole.MANAGER))
    """
    async def _checker(session: TmaSession = Depends(get_tma_session)) -> TmaSession:
        if session.role not in allowed:
            raise HTTPException(403, "Недостаточно прав")
        return session
    return _checker
