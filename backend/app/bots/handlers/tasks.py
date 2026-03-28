"""Task handlers — create, list, view, update, delete, subtasks, notes, digest."""
from datetime import datetime
from uuid import UUID

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.db.session import AsyncSessionLocal
from app.db.models import Task, TaskStatus, TaskPriority, Note
from app.db.repositories import TaskRepository, ProjectRepository, UserRepository
from app.services.ai_service import parse_task_from_text
from app.bots.keyboards import (
    tasks_list_keyboard, task_detail_keyboard,
    priority_keyboard, projects_keyboard, main_menu_keyboard, confirm_keyboard,
)

router = Router()


class AddTaskFSM(StatesGroup):
    waiting_for_text = State()
    waiting_for_project = State()
    waiting_for_priority = State()


class EditTaskFSM(StatesGroup):
    waiting_for_title = State()


class SubtaskFSM(StatesGroup):
    waiting_for_title = State()


class NoteFSM(StatesGroup):
    waiting_for_text = State()


# ─── List tasks ───────────────────────────────────────────────────────────────

@router.message(Command("tasks"))
@router.callback_query(F.data == "tasks:my")
async def show_my_tasks(event, workspace_id: str, state: FSMContext = None):
    if state:
        await state.clear()
    is_callback = isinstance(event, CallbackQuery)
    user_tg_id = event.from_user.id

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_tg_id)
        if not user:
            text = "Сначала выполни /start"
            if is_callback:
                await event.answer(text, show_alert=True)
            else:
                await event.answer(text)
            return

        task_repo = TaskRepository(session)
        tasks = await task_repo.get_user_tasks(user.id, UUID(workspace_id))

    if not tasks:
        text = "У тебя нет активных задач 🎉\n\nДобавь первую задачу:"
    else:
        text = f"<b>Твои задачи</b> ({len(tasks)}):"

    keyboard = tasks_list_keyboard(tasks)
    if is_callback:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard)


# ─── Add task ─────────────────────────────────────────────────────────────────

@router.message(Command("add"))
@router.callback_query(F.data == "tasks:add")
async def start_add_task(event, state: FSMContext):
    is_callback = isinstance(event, CallbackQuery)
    text = (
        "📝 <b>Новая задача</b>\n\n"
        "Опиши задачу в свободной форме, например:\n"
        "<i>«Сдать отчёт в пятницу, высокий приоритет»</i>\n"
        "<i>«Купить продукты завтра»</i>\n\n"
        "Или просто напиши название."
    )
    await state.set_state(AddTaskFSM.waiting_for_text)
    if is_callback:
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)


@router.message(AddTaskFSM.waiting_for_text)
async def process_task_text(message: Message, state: FSMContext, workspace_id: str):
    user_input = message.text.strip()
    await message.answer("🤖 Анализирую задачу...")

    parsed = await parse_task_from_text(user_input)
    await state.update_data(parsed=parsed)

    due_str = ""
    if parsed.get("due_date"):
        try:
            dt = datetime.fromisoformat(parsed["due_date"])
            due_str = f"\n📅 Дедлайн: {dt.strftime('%d.%m.%Y %H:%M')}"
        except Exception:
            pass

    text = (
        f"<b>Распознал задачу:</b>\n"
        f"📋 {parsed['title']}{due_str}\n"
        f"⚡ Приоритет: {parsed.get('priority', 'medium')}\n\n"
        "Выбери проект:"
    )

    async with AsyncSessionLocal() as session:
        proj_repo = ProjectRepository(session)
        projects = await proj_repo.get_workspace_projects(UUID(workspace_id))

    if not projects:
        await message.answer(
            "Нет доступных проектов. Сначала создай проект через /projects",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    await state.set_state(AddTaskFSM.waiting_for_project)
    await message.answer(text, reply_markup=projects_keyboard(projects, mode="select"))


@router.callback_query(F.data.startswith("project:select:"), AddTaskFSM.waiting_for_project)
async def process_task_project(callback: CallbackQuery, state: FSMContext):
    project_id = callback.data.split(":")[2]
    await state.update_data(project_id=project_id)
    await state.set_state(AddTaskFSM.waiting_for_priority)
    await callback.message.edit_text(
        "Выбери приоритет задачи:",
        reply_markup=priority_keyboard("task:priority"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:priority:"), AddTaskFSM.waiting_for_priority)
async def process_task_priority(callback: CallbackQuery, state: FSMContext):
    priority = callback.data.split(":")[2]
    data = await state.get_data()
    parsed = data["parsed"]
    parsed["priority"] = priority

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        task_repo = TaskRepository(session)

        due_date = None
        if parsed.get("due_date"):
            try:
                due_date = datetime.fromisoformat(parsed["due_date"])
            except Exception:
                pass

        task = Task(
            project_id=UUID(data["project_id"]),
            creator_id=user.id,
            assignee_id=user.id,
            title=parsed["title"],
            description=parsed.get("description"),
            priority=TaskPriority(priority),
            due_date=due_date,
        )
        task = await task_repo.save(task)
        await session.commit()
        task_id = str(task.id)

    await state.clear()
    due_str = f"\n📅 {due_date.strftime('%d.%m.%Y %H:%M')}" if due_date else ""
    priority_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}
    await callback.message.edit_text(
        f"✅ <b>Задача создана!</b>\n\n"
        f"📋 {parsed['title']}{due_str}\n"
        f"{priority_icons.get(priority, '🟡')} Приоритет: {priority}",
        reply_markup=task_detail_keyboard(task_id, "todo"),
    )
    await callback.answer("Задача добавлена!")


# ─── View task ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:view:"))
async def view_task(callback: CallbackQuery):
    task_id = callback.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get_with_subtasks(UUID(task_id))

    if not task:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    status_icons = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}
    priority_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}

    status = task.status.value
    priority = task.priority.value
    due_str = f"\n📅 Дедлайн: <b>{task.due_date.strftime('%d.%m.%Y %H:%M')}</b>" if task.due_date else ""
    desc_str = f"\n\n📄 {task.description}" if task.description else ""

    subtasks_str = ""
    if task.subtasks:
        subtasks_str = "\n\n<b>Подзадачи:</b>"
        for st in task.subtasks:
            icon = status_icons.get(st.status.value, "⬜")
            subtasks_str += f"\n{icon} {st.title}"

    notes_str = ""
    if task.notes:
        notes_str = "\n\n<b>Заметки:</b>"
        for note in task.notes[-3:]:
            notes_str += f"\n• {note.content}"

    text = (
        f"{status_icons.get(status, '⬜')} <b>{task.title}</b>\n"
        f"{priority_icons.get(priority, '🟡')} Приоритет: {priority}"
        f"{due_str}{desc_str}{subtasks_str}{notes_str}"
    )
    await callback.message.edit_text(text, reply_markup=task_detail_keyboard(task_id, status))
    await callback.answer()


# ─── Update task status ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:done:"))
async def mark_task_done(callback: CallbackQuery, workspace_id: str, state: FSMContext):
    task_id = callback.data.split(":")[2]
    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(UUID(task_id))
        if task:
            task.status = TaskStatus.DONE
            task.completed_at = datetime.utcnow()
            await session.commit()
    await callback.answer("✅ Задача выполнена!")
    await show_my_tasks(callback, workspace_id=workspace_id, state=state)


@router.callback_query(F.data.startswith("task:progress:"))
async def mark_task_in_progress(callback: CallbackQuery):
    task_id = callback.data.split(":")[2]
    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(UUID(task_id))
        if task:
            task.status = TaskStatus.IN_PROGRESS
            await session.commit()
    await callback.answer("🔄 Задача в работе!")
    await view_task(callback)


# ─── Edit task ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:edit:"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":")[2]
    await state.set_state(EditTaskFSM.waiting_for_title)
    await state.update_data(task_id=task_id)
    await callback.message.edit_text(
        "✏️ Введи новое название задачи:"
    )
    await callback.answer()


@router.message(EditTaskFSM.waiting_for_title)
async def process_edit_title(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["task_id"]
    new_title = message.text.strip()

    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(UUID(task_id))
        if task:
            task.title = new_title
            await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Название обновлено: <b>{new_title}</b>",
        reply_markup=task_detail_keyboard(task_id, "todo"),
    )


# ─── Add subtask ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:subtask:"))
async def start_add_subtask(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":")[2]
    await state.set_state(SubtaskFSM.waiting_for_title)
    await state.update_data(parent_id=task_id)
    await callback.message.edit_text("➕ Введи название подзадачи:")
    await callback.answer()


@router.message(SubtaskFSM.waiting_for_title)
async def process_subtask_title(message: Message, state: FSMContext):
    data = await state.get_data()
    parent_id = data["parent_id"]
    title = message.text.strip()

    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        parent = await task_repo.get(UUID(parent_id))
        if not parent:
            await message.answer("Задача не найдена")
            await state.clear()
            return

        subtask = Task(
            project_id=parent.project_id,
            parent_id=UUID(parent_id),
            creator_id=parent.creator_id,
            assignee_id=parent.assignee_id,
            title=title,
        )
        await task_repo.save(subtask)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Подзадача добавлена: <b>{title}</b>",
        reply_markup=task_detail_keyboard(parent_id, "todo"),
    )


# ─── Add note ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:note:"))
async def start_add_note(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":")[2]
    await state.set_state(NoteFSM.waiting_for_text)
    await state.update_data(task_id=task_id)
    await callback.message.edit_text("📝 Введи текст заметки:")
    await callback.answer()


@router.message(NoteFSM.waiting_for_text)
async def process_note_text(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["task_id"]
    content = message.text.strip()

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        note = Note(
            task_id=UUID(task_id),
            user_id=user.id,
            content=content,
        )
        session.add(note)
        await session.commit()

    await state.clear()
    await message.answer(
        "📝 Заметка сохранена!",
        reply_markup=task_detail_keyboard(task_id, "todo"),
    )


# ─── Delete task ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task:delete:"))
async def confirm_delete_task(callback: CallbackQuery):
    task_id = callback.data.split(":")[2]
    await callback.message.edit_text(
        "🗑️ Удалить задачу? Это действие необратимо.",
        reply_markup=confirm_keyboard(
            yes_data=f"task:delete_confirm:{task_id}",
            no_data=f"task:view:{task_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:delete_confirm:"))
async def delete_task(callback: CallbackQuery, workspace_id: str, state: FSMContext):
    task_id = callback.data.split(":")[2]
    async with AsyncSessionLocal() as session:
        task_repo = TaskRepository(session)
        task = await task_repo.get(UUID(task_id))
        if task:
            await task_repo.delete(task)
            await session.commit()
    await callback.answer("🗑️ Задача удалена")
    await show_my_tasks(callback, workspace_id=workspace_id, state=state)


# ─── Daily digest ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "digest:today")
async def show_today_digest(callback: CallbackQuery, workspace_id: str):
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала выполни /start", show_alert=True)
            return

        task_repo = TaskRepository(session)
        tasks = await task_repo.get_user_tasks(user.id, UUID(workspace_id))

    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59)
    today_tasks = [t for t in tasks if t.due_date and t.due_date <= today_end]
    overdue = [t for t in today_tasks if t.due_date < datetime.utcnow()]
    due_today = [t for t in today_tasks if t.due_date >= datetime.utcnow()]

    if not today_tasks:
        text = f"☀️ <b>Дайджест на сегодня</b>\n\nНет задач на сегодня 🎉\n\nВсего активных: {len(tasks)}"
    else:
        lines = [f"☀️ <b>Дайджест на сегодня</b>"]
        if overdue:
            lines.append(f"\n🔴 <b>Просрочено ({len(overdue)}):</b>")
            for t in overdue[:5]:
                lines.append(f"• {t.title}")
        if due_today:
            lines.append(f"\n📅 <b>На сегодня ({len(due_today)}):</b>")
            for t in due_today[:5]:
                time_str = t.due_date.strftime("%H:%M")
                lines.append(f"• {t.title} — {time_str}")
        lines.append(f"\nВсего активных: {len(tasks)}")
        text = "\n".join(lines)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Все задачи", callback_data="tasks:my"))
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ─── Main menu callback ───────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def go_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


# ─── Free text → AI task ──────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_free_text(message: Message, state: FSMContext, workspace_id: str):
    current_state = await state.get_state()
    if current_state:
        return
    await start_add_task(message, state)
