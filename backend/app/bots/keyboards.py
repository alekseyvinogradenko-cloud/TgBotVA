"""Reusable keyboard builders."""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Мои задачи", callback_data="tasks:my"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="tasks:add"),
    )
    builder.row(
        InlineKeyboardButton(text="📁 Проекты", callback_data="projects:list"),
        InlineKeyboardButton(text="📊 Дайджест", callback_data="digest:today"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu"),
    )
    return builder.as_markup()


def tasks_list_keyboard(tasks: list, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        status_icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}.get(
            task.status.value if hasattr(task.status, "value") else task.status, "⬜"
        )
        priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}.get(
            task.priority.value if hasattr(task.priority, "value") else task.priority, "🟡"
        )
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon}{priority_icon} {task.title[:40]}",
                callback_data=f"task:view:{task.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ Новая задача", callback_data="tasks:add"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def task_detail_keyboard(task_id: str, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status != "done":
        builder.row(
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"task:done:{task_id}"),
            InlineKeyboardButton(text="🔄 В работе", callback_data=f"task:progress:{task_id}"),
        )
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"task:edit:{task_id}"),
        InlineKeyboardButton(text="➕ Подзадача", callback_data=f"task:subtask:{task_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Заметка", callback_data=f"task:note:{task_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"task:delete:{task_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="tasks:my"),
    )
    return builder.as_markup()


def priority_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🟢 Низкий", callback_data=f"{callback_prefix}:low"),
        InlineKeyboardButton(text="🟡 Средний", callback_data=f"{callback_prefix}:medium"),
    )
    builder.row(
        InlineKeyboardButton(text="🟠 Высокий", callback_data=f"{callback_prefix}:high"),
        InlineKeyboardButton(text="🔴 Срочный", callback_data=f"{callback_prefix}:urgent"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Отмена", callback_data="tasks:my"),
    )
    return builder.as_markup()


def projects_keyboard(projects: list, mode: str = "view") -> InlineKeyboardMarkup:
    """mode='view' — открыть проект, mode='select' — выбрать проект для задачи."""
    builder = InlineKeyboardBuilder()
    for p in projects:
        callback = f"project:{mode}:{p.id}"
        builder.row(
            InlineKeyboardButton(text=f"📁 {p.name}", callback_data=callback)
        )
    builder.row(
        InlineKeyboardButton(text="➕ Новый проект", callback_data="project:create"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
    )
    return builder.as_markup()
