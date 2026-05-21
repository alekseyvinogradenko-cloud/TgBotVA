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
from app.bots.manager import bot_manager
from app.db.session import get_db
from app.db.models import Note, Project, Task, TaskStatus, TaskPriority, User, Workspace
from app.db.repositories import TaskRepository, ProjectRepository
from app.services.ai_service import parse_task_from_text

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _notify_assignee(
    db: AsyncSession,
    workspace_id: UUID,
    assignee: Optional[User],
    actor: User,
    task_title: str,
    reassigned: bool = False,
) -> None:
    """DM the assignee that a task was (re)assigned to them. No-op for self-assignment."""
    if not assignee or assignee.id == actor.id:
        return
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        return
    verb = "переназначена" if reassigned else "назначена"
    text = (
        f"📬 <b>Тебе {verb} задача</b>\n\n"
        f"📋 {task_title}\n"
        f"👤 От: {actor.first_name}"
    )
    await bot_manager.send_message(ws.telegram_bot_token, assignee.telegram_id, text)


async def _assert_member(db: AsyncSession, workspace_id: UUID, user_id: Optional[UUID]) -> None:
    """Reject assignee_id that isn't a member of the workspace."""
    if user_id is None:
        return
    from app.db.models import WorkspaceMember
    res = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .where(WorkspaceMember.user_id == user_id)
    )
    if not res.scalar_one_or_none():
        raise HTTPException(400, "Assignee is not a member of this workspace")


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


# ─── Parse free-text via AI ───────────────────────────────────────────────────

class ParseTaskRequest(BaseModel):
    text: str


class ParseTaskResponse(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    project_hint: Optional[str] = None


@router.post("/parse", response_model=ParseTaskResponse)
async def parse_task_text(
    body: ParseTaskRequest,
    session: TmaSession = Depends(get_tma_session),
):
    """Run user text through the AI parser using their preferred model."""
    parsed = await parse_task_from_text(body.text, model=session.user.ai_model)

    due: Optional[datetime] = None
    if parsed.get("due_date"):
        try:
            due = datetime.fromisoformat(str(parsed["due_date"]).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            due = None

    try:
        priority = TaskPriority(parsed.get("priority", "medium"))
    except ValueError:
        priority = TaskPriority.MEDIUM

    return ParseTaskResponse(
        title=str(parsed.get("title") or body.text)[:512],
        description=parsed.get("description"),
        due_date=due,
        priority=priority,
        project_hint=parsed.get("project_hint"),
    )


# ─── Create task (TMA-authed) ─────────────────────────────────────────────────

class TmaCreateTaskRequest(BaseModel):
    project_id: UUID
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[UUID] = None  # default = creator (Stage 5 wires picker)


@router.post("/create", response_model=TaskListItem, status_code=201)
async def create_task_tma(
    body: TmaCreateTaskRequest,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    # Verify project belongs to caller's workspace
    project = await db.get(Project, body.project_id)
    if not project or project.workspace_id != session.workspace_id:
        raise HTTPException(404, "Project not found in this workspace")

    await _assert_member(db, session.workspace_id, body.assignee_id)

    task = Task(
        project_id=body.project_id,
        creator_id=session.user.id,
        assignee_id=body.assignee_id or session.user.id,
        title=body.title.strip(),
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    assignee = await db.get(User, task.assignee_id) if task.assignee_id else None
    await _notify_assignee(db, session.workspace_id, assignee, session.user, task.title)
    now = datetime.now(timezone.utc)
    is_overdue = bool(task.due_date and task.due_date < now and task.status != TaskStatus.DONE)

    return TaskListItem(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project=ProjectMini(id=project.id, name=project.name, color=project.color),
        assignee=AssigneeMini(
            id=assignee.id,
            first_name=assignee.first_name,
            initials=_initials(assignee.first_name, assignee.last_name),
        ) if assignee else None,
        is_overdue=is_overdue,
    )


# ─── List ────────────────────────────────────────────────────────────────────

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


# ─── Task detail + mutations (TMA-authed, scope-checked) ──────────────────────

class NoteItem(BaseModel):
    id: UUID
    content: str
    created_at: datetime


class SubtaskItem(BaseModel):
    id: UUID
    title: str
    status: TaskStatus


class TaskDetail(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    is_overdue: bool
    project: ProjectMini
    assignee: Optional[AssigneeMini]
    subtasks: list[SubtaskItem]
    notes: list[NoteItem]


async def _owned_task(task_id: UUID, session: TmaSession, db: AsyncSession) -> Task:
    """Fetch a task and assert it belongs to the caller's workspace.
    Returns 404 (not 403) so we don't leak existence of other-workspace tasks."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    project = await db.get(Project, task.project_id)
    if not project or project.workspace_id != session.workspace_id:
        raise HTTPException(404, "Task not found")
    return task


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task_detail(
    task_id: UUID,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    await _owned_task(task_id, session, db)
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.subtasks),
            selectinload(Task.notes),
            selectinload(Task.assignee),
            selectinload(Task.project),
        )
        .where(Task.id == task_id)
    )
    task = result.scalar_one()
    now = datetime.now(timezone.utc)
    return TaskDetail(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        is_overdue=bool(task.due_date and task.due_date < now and task.status != TaskStatus.DONE),
        project=ProjectMini(id=task.project.id, name=task.project.name, color=task.project.color),
        assignee=AssigneeMini(
            id=task.assignee.id,
            first_name=task.assignee.first_name,
            initials=_initials(task.assignee.first_name, task.assignee.last_name),
        ) if task.assignee else None,
        subtasks=[
            SubtaskItem(id=s.id, title=s.title, status=s.status)
            for s in sorted(task.subtasks, key=lambda x: x.created_at or now)
        ],
        notes=[
            NoteItem(id=n.id, content=n.content, created_at=n.created_at)
            for n in sorted(task.notes, key=lambda x: x.created_at or now)
        ],
    )


class StatusUpdate(BaseModel):
    status: TaskStatus


@router.post("/{task_id}/status", status_code=204)
async def set_task_status(
    task_id: UUID,
    body: StatusUpdate,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(task_id, session, db)
    task.status = body.status
    if body.status == TaskStatus.DONE:
        task.completed_at = datetime.now(timezone.utc)
    elif task.completed_at:
        task.completed_at = None
    await db.commit()


class TaskEdit(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[UUID] = None


@router.post("/{task_id}/update", status_code=204)
async def edit_task(
    task_id: UUID,
    body: TaskEdit,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(task_id, session, db)
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"]:
        task.title = data["title"].strip()[:512]
    if "description" in data:
        task.description = data["description"]
    if "due_date" in data:
        task.due_date = data["due_date"]
    if "priority" in data and data["priority"]:
        task.priority = data["priority"]

    reassigned_to: Optional[User] = None
    if "assignee_id" in data and data["assignee_id"] and data["assignee_id"] != task.assignee_id:
        await _assert_member(db, session.workspace_id, data["assignee_id"])
        task.assignee_id = data["assignee_id"]
        reassigned_to = await db.get(User, data["assignee_id"])

    await db.commit()

    if reassigned_to:
        await _notify_assignee(
            db, session.workspace_id, reassigned_to, session.user, task.title, reassigned=True
        )


@router.post("/{task_id}/delete", status_code=204)
async def delete_task_tma(
    task_id: UUID,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(task_id, session, db)
    await db.delete(task)
    await db.commit()


class SubtaskCreate(BaseModel):
    title: str


@router.post("/{task_id}/subtask", response_model=SubtaskItem, status_code=201)
async def add_subtask(
    task_id: UUID,
    body: SubtaskCreate,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    parent = await _owned_task(task_id, session, db)
    subtask = Task(
        project_id=parent.project_id,
        parent_id=parent.id,
        creator_id=session.user.id,
        assignee_id=parent.assignee_id or session.user.id,
        title=body.title.strip()[:512],
    )
    db.add(subtask)
    await db.commit()
    await db.refresh(subtask)
    return SubtaskItem(id=subtask.id, title=subtask.title, status=subtask.status)


class NoteCreate(BaseModel):
    content: str


@router.post("/{task_id}/note", response_model=NoteItem, status_code=201)
async def add_note(
    task_id: UUID,
    body: NoteCreate,
    session: TmaSession = Depends(get_tma_session),
    db: AsyncSession = Depends(get_db),
):
    await _owned_task(task_id, session, db)
    note = Note(
        task_id=task_id,
        user_id=session.user.id,
        content=body.content.strip(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteItem(id=note.id, content=note.content, created_at=note.created_at)


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
