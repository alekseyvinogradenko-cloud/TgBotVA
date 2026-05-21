"""Projects REST API — TMA-authed (Telegram Mini App)."""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TmaSession, get_tma_session, require_role
from app.db.session import get_db
from app.db.models import Project, UserRole

router = APIRouter(prefix="/projects", tags=["projects"])


# ─── TMA endpoints ────────────────────────────────────────────────────────────

class ProjectMiniResponse(BaseModel):
    id: UUID
    name: str
    color: str
    description: Optional[str] = None
    is_archived: bool = False

    model_config = {"from_attributes": True}


@router.get("/mine", response_model=list[ProjectMiniResponse])
async def get_my_workspace_projects(
    include_archived: bool = False,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    """Return projects in the caller's current workspace (active by default)."""
    from sqlalchemy import select
    q = select(Project).where(Project.workspace_id == session.workspace_id)
    if not include_archived:
        q = q.where(Project.is_archived == False)  # noqa: E712
    q = q.order_by(Project.is_archived, Project.name)
    result = await db.execute(q)
    return list(result.scalars().all())


class ProjectCreateTma(BaseModel):
    name: str
    color: str = "#6366f1"


@router.post("/create", response_model=ProjectMiniResponse, status_code=201)
async def create_project_tma(
    body: ProjectCreateTma,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    if len(name) < 2:
        raise HTTPException(400, "Название слишком короткое")
    project = Project(
        workspace_id=session.workspace_id,
        name=name[:256],
        color=body.color or "#6366f1",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


class ArchiveBody(BaseModel):
    archived: bool


@router.post("/{project_id}/archive", status_code=204)
async def archive_project_tma(
    project_id: UUID,
    body: ArchiveBody,
    session: TmaSession = Depends(require_role(UserRole.OWNER, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.workspace_id != session.workspace_id:
        raise HTTPException(404, "Project not found")
    project.is_archived = body.archived
    await db.commit()


# Legacy unauthenticated endpoints (GET /workspace/{id}, POST /, PATCH /{id},
# DELETE /{id}) were removed — they allowed public CRUD on any workspace's
# projects. The Mini App uses /mine, /create and /{id}/archive (TMA-authed).
