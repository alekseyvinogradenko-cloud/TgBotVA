from uuid import UUID

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import AsyncSessionLocal
from app.db.models import Workspace, WorkspaceMember, UserRole
from app.db.repositories import UserRepository
from app.bots.keyboards import main_menu_keyboard
from sqlalchemy import select

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, workspace_id: str, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user, created = await user_repo.get_or_create(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            telegram_username=message.from_user.username,
            language_code=message.from_user.language_code or "ru",
        )

        workspace = await session.get(Workspace, UUID(workspace_id))
        if workspace:
            existing = await session.execute(
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace.id)
                .where(WorkspaceMember.user_id == user.id)
            )
            if not existing.scalar_one_or_none():
                member = WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=UserRole.EXECUTOR,
                )
                session.add(member)

        await session.commit()

    greeting = "Добро пожаловать" if created else "С возвращением"
    await message.answer(
        f"{greeting}, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "Я твой персональный ассистент. Вот что я умею:\n\n"
        "📋 Управлять задачами и проектами\n"
        "🔔 Напоминать о дедлайнах\n"
        "🤖 Понимать задачи из обычного текста\n"
        "📊 Присылать дайджесты\n\n"
        "Выбери действие:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start — главное меню\n"
        "/tasks — мои задачи\n"
        "/add — добавить задачу\n"
        "/projects — проекты\n"
        "/settings — настройки\n"
        "/help — эта справка\n\n"
        "<b>Быстрый ввод:</b>\n"
        "Просто напиши задачу текстом, например:\n"
        "<i>«Купить молоко завтра в 18:00»</i>\n"
        "<i>«Сдать отчёт в пятницу — высокий приоритет»</i>"
    )
