"""Tasks REST API — used by the web frontend."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Task, TaskStatus, TaskPriority
from app.db.repositories import TaskRepository, ProjectRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    project_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    assignee_id: Optional[UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[UUID] = None


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    parent_id: Optional[UUID]
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/workspace/{workspace_id}")
async def get_workspace_tasks(
    workspace_id: UUID,
    status: Optional[TaskStatus] = None,
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    from sqlalchemy import select
    from app.db.models import Project

    q = select(Task).join(Project).where(Project.workspace_id == workspace_id)
    if status:
        q = q.where(Task.status == status)
    q = q.order_by(Task.due_date.nulls_last(), Task.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    repo = TaskRepository(db)
    task = Task(**body.model_dump())
    task = await repo.save(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = TaskRepository(db)
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    if body.status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = TaskRepository(db)
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    await repo.delete(task)
    await db.commit()
