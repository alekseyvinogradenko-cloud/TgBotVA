"""Base repository and domain repositories."""
from typing import Generic, TypeVar, Type, Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Base, User, Workspace, WorkspaceMember, Project, Task, Reminder, Note,
    TaskStatus, UserRole
)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    model: Type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID) -> Optional[T]:
        return await self.session.get(self.model, id)

    async def save(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: T) -> None:
        await self.session.delete(obj)
        await self.session.flush()


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, **kwargs) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user, False
        user = User(telegram_id=telegram_id, **kwargs)
        await self.save(user)
        return user, True


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def get_by_bot_token(self, token: str) -> Optional[Workspace]:
        result = await self.session.execute(
            select(Workspace)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
            .where(Workspace.telegram_bot_token == token)
        )
        return result.scalar_one_or_none()

    async def get_user_workspaces(self, user_id: UUID) -> List[Workspace]:
        result = await self.session.execute(
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .where(Workspace.is_active == True)
        )
        return list(result.scalars().all())


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_workspace_projects(self, workspace_id: UUID) -> List[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .where(Project.is_archived == False)
            .order_by(Project.name)
        )
        return list(result.scalars().all())


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_project_tasks(
        self, project_id: UUID, status: Optional[TaskStatus] = None
    ) -> List[Task]:
        q = select(Task).where(Task.project_id == project_id).where(Task.parent_id == None)
        if status:
            q = q.where(Task.status == status)
        q = q.order_by(Task.due_date.nulls_last(), Task.priority)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_user_tasks(
        self, user_id: UUID, workspace_id: Optional[UUID] = None
    ) -> List[Task]:
        q = (
            select(Task)
            .join(Project)
            .where(Task.assignee_id == user_id)
            .where(Task.status != TaskStatus.DONE)
            .where(Task.status != TaskStatus.CANCELLED)
        )
        if workspace_id:
            q = q.where(Project.workspace_id == workspace_id)
        q = q.order_by(Task.due_date.nulls_last())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_with_subtasks(self, task_id: UUID) -> Optional[Task]:
        result = await self.session.execute(
            select(Task)
            .options(selectinload(Task.subtasks), selectinload(Task.notes))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
