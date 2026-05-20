"""
FastAPI dependencies — TMA (Telegram Mini App) Bearer auth.
"""
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db


class TmaSession:
    """Authenticated mini-app caller — user + workspace scope."""
    def __init__(self, user: User, workspace_id: UUID):
        self.user = user
        self.workspace_id = workspace_id


async def get_tma_session(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> TmaSession:
    """Parse `Authorization: Bearer <jwt>`, return the active TMA session.

    Raises 401 on missing/invalid/expired token.
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

    return TmaSession(user=user, workspace_id=workspace_id)
