"""Tasks REST API — used by the web frontend."""
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import TmaSession, get_tma_session
from app.db.session import get_db
from app.db.models import Project, Task, TaskStatus, TaskPriority
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


# ─── TMA Mini App models ──────────────────────────────────────────────────────

class ProjectMini(BaseModel):
    id: UUID
    name: str
    color: str


class AssigneeMini(BaseModel):
    id: UUID
    first_name: str
    initials: str


class TaskListItem(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    project: ProjectMini
    assignee: Optional[AssigneeMini]
    is_overdue: bool


def _initials(first_name: str, last_name: Optional[str]) -> str:
    f = (first_name or "").strip()
    l = (last_name or "").strip()
    s = (f[:1] + (l[:1] if l else "")).upper()
    return s or "—"


@router.get("/mine", response_model=list[TaskListItem])
async def get_my_tasks(
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    """Return active (todo/in_progress) tasks assigned to the current TMA user
    in their current workspace, with project + assignee info for rendering."""
    now = datetime.now(timezone.utc)

    q = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .options(selectinload(Task.assignee), selectinload(Task.project))
        .where(Task.assignee_id == session.user.id)
        .where(Project.workspace_id == session.workspace_id)
        .where(Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]))
        .order_by(Task.due_date.nulls_last(), Task.created_at.desc())
    )
    result = await db.execute(q)
    tasks = result.scalars().all()

    items: list[TaskListItem] = []
    for t in tasks:
        assignee_info = None
        if t.assignee:
            assignee_info = AssigneeMini(
                id=t.assignee.id,
                first_name=t.assignee.first_name,
                initials=_initials(t.assignee.first_name, t.assignee.last_name),
            )
        is_overdue = bool(
            t.due_date and t.due_date < now and t.status != TaskStatus.DONE
        )
        items.append(
            TaskListItem(
                id=t.id,
                title=t.title,
                description=t.description,
                status=t.status,
                priority=t.priority,
                due_date=t.due_date,
                project=ProjectMini(id=t.project.id, name=t.project.name, color=t.project.color),
                assignee=assignee_info,
                is_overdue=is_overdue,
            )
        )
    return items


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
