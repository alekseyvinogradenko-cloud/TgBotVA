"""Projects REST API — used by the web frontend."""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
