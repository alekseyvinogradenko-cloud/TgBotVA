"""Projects REST API — used by the web frontend."""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TmaSession, get_tma_session
from app.db.session import get_db
from app.db.models import Project
from app.db.repositories import ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_archived: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    color: str
    is_archived: bool

    model_config = {"from_attributes": True}


@router.get("/workspace/{workspace_id}", response_model=list[ProjectResponse])
async def get_workspace_projects(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)
    return await repo.get_workspace_projects(workspace_id)


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
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.workspace_id != session.workspace_id:
        raise HTTPException(404, "Project not found")
    project.is_archived = body.archived
    await db.commit()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    repo = ProjectRepository(db)
    project = Project(**body.model_dump())
    project = await repo.save(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await repo.delete(project)
    await db.commit()
