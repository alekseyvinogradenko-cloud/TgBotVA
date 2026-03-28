"""Project handlers."""
from uuid import UUID

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.session import AsyncSessionLocal
from app.db.models import Project
from app.db.repositories import ProjectRepository, TaskRepository
from app.bots.keyboards import projects_keyboard, tasks_list_keyboard, main_menu_keyboard

router = Router()


class CreateProjectFSM(StatesGroup):
    waiting_for_name = State()


@router.message(Command("projects"))
@router.callback_query(F.data == "projects:list")
async def show_projects(event, workspace_id: str, state: FSMContext):
    await state.clear()
    is_callback = isinstance(event, CallbackQuery)

    async with AsyncSessionLocal() as session:
        repo = ProjectRepository(session)
        projects = await repo.get_workspace_projects(UUID(workspace_id))

    text = f"<b>Проекты</b> ({len(projects)}):" if projects else "Нет проектов. Создай первый!"
    keyboard = projects_keyboard(projects)

    if is_callback:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "project:create")
async def start_create_project(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateProjectFSM.waiting_for_name)
    await callback.message.edit_text(
        "📁 <b>Новый проект</b>\n\nВведи название проекта:"
    )
    await callback.answer()


@router.message(CreateProjectFSM.waiting_for_name)
async def process_project_name(message: Message, state: FSMContext, workspace_id: str):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Название слишком короткое, попробуй ещё раз:")
        return

    async with AsyncSessionLocal() as session:
        repo = ProjectRepository(session)
        project = Project(workspace_id=UUID(workspace_id), name=name)
        await repo.save(project)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Проект <b>{name}</b> создан!",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("project:view:"))
async def view_project(callback: CallbackQuery, workspace_id: str):
    project_id = callback.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        proj_repo = ProjectRepository(session)
        project = await proj_repo.get(UUID(project_id))
        task_repo = TaskRepository(session)
        tasks = await task_repo.get_project_tasks(UUID(project_id))

    if not project:
        await callback.answer("Проект не найден", show_alert=True)
        return

    todo = sum(1 for t in tasks if t.status.value == "todo")
    in_progress = sum(1 for t in tasks if t.status.value == "in_progress")
    done = sum(1 for t in tasks if t.status.value == "done")

    text = (
        f"📁 <b>{project.name}</b>\n\n"
        f"⬜ К выполнению: {todo}\n"
        f"🔄 В работе: {in_progress}\n"
        f"✅ Выполнено: {done}\n"
        f"Всего: {len(tasks)}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Все задачи", callback_data=f"project:tasks:{project_id}"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="tasks:add"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Проекты", callback_data="projects:list"),
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("project:tasks:"))
async def view_project_tasks(callback: CallbackQuery):
    project_id = callback.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        proj_repo = ProjectRepository(session)
        project = await proj_repo.get(UUID(project_id))
        task_repo = TaskRepository(session)
        tasks = await task_repo.get_project_tasks(UUID(project_id))

    if not project:
        await callback.answer("Проект не найден", show_alert=True)
        return

    active_tasks = [t for t in tasks if t.status.value not in ("done", "cancelled")]

    from app.bots.keyboards import tasks_list_keyboard
    text = f"📁 <b>{project.name}</b> — задачи ({len(active_tasks)}):"
    if not active_tasks:
        text = f"📁 <b>{project.name}</b>\n\nЗадач нет. Добавь первую!"

    builder_back = InlineKeyboardBuilder()
    builder_back.row(
        InlineKeyboardButton(text="◀️ К проекту", callback_data=f"project:view:{project_id}"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="tasks:add"),
    )

    from app.bots.keyboards import tasks_list_keyboard as tlk
    keyboard = tlk(active_tasks) if active_tasks else builder_back.as_markup()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
