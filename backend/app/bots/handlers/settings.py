"""Settings handlers — notifications, timezone, AI model."""
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.session import AsyncSessionLocal
from app.db.repositories import UserRepository

router = Router()

AI_MODELS = [
    ("gpt-4o", "GPT-4o (умный, дорогой)"),
    ("gpt-4o-mini", "GPT-4o Mini (быстрый, дешёвый)"),
    ("gpt-3.5-turbo", "GPT-3.5 Turbo (базовый)"),
]


def settings_keyboard(user) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    morning = "✅" if user.notify_morning_digest else "❌"
    weekly = "✅" if user.notify_weekly_report else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"{morning} Утренний дайджест ({user.notify_morning_time})",
            callback_data="settings:toggle:morning",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{weekly} Еженедельный отчёт",
            callback_data="settings:toggle:weekly",
        )
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Время дайджеста", callback_data="settings:morning_time"),
        InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="settings:timezone"),
    )
    builder.row(
        InlineKeyboardButton(text=f"🤖 AI: {user.ai_model}", callback_data="settings:ai_model"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
    )
    return builder.as_markup()


@router.message(Command("settings"))
@router.callback_query(F.data == "settings:menu")
async def show_settings(event, state: FSMContext):
    await state.clear()
    is_callback = isinstance(event, CallbackQuery)
    tg_id = event.from_user.id

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(tg_id)

    text = "⚙️ <b>Настройки</b>"
    keyboard = settings_keyboard(user)

    if is_callback:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("settings:toggle:"))
async def toggle_setting(callback: CallbackQuery):
    key = callback.data.split(":")[2]
    tg_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(tg_id)
        if key == "morning":
            user.notify_morning_digest = not user.notify_morning_digest
        elif key == "weekly":
            user.notify_weekly_report = not user.notify_weekly_report
        await session.commit()
        await session.refresh(user)

    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(user))
    await callback.answer("Настройка обновлена")


# ─── Morning time ─────────────────────────────────────────────────────────────

class SetMorningTimeFSM(StatesGroup):
    waiting_for_time = State()


@router.callback_query(F.data == "settings:morning_time")
async def ask_morning_time(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SetMorningTimeFSM.waiting_for_time)
    await callback.message.edit_text(
        "Введи время утреннего дайджеста в формате <b>HH:MM</b>\n"
        "Например: <code>09:00</code>"
    )
    await callback.answer()


@router.message(SetMorningTimeFSM.waiting_for_time)
async def set_morning_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer("Неверный формат. Используй HH:MM, например 09:00")
        return

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
        user.notify_morning_time = time_str
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Время дайджеста установлено: <b>{time_str}</b>")


# ─── Timezone ─────────────────────────────────────────────────────────────────

class SetTimezoneFSM(StatesGroup):
    waiting_for_tz = State()

COMMON_TZ = [
    "Europe/Moscow", "Europe/Kiev", "Asia/Almaty",
    "Europe/Minsk", "Asia/Tashkent", "Europe/London",
]


@router.callback_query(F.data == "settings:timezone")
async def ask_timezone(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SetTimezoneFSM.waiting_for_tz)
    builder = InlineKeyboardBuilder()
    for tz in COMMON_TZ:
        builder.row(InlineKeyboardButton(text=tz, callback_data=f"settings:tz_set:{tz}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="settings:menu"))
    await callback.message.edit_text(
        "🌍 Выбери часовой пояс или введи вручную (например <code>Europe/Moscow</code>):",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:tz_set:"))
async def set_timezone_from_button(callback: CallbackQuery, state: FSMContext):
    tz = ":".join(callback.data.split(":")[2:])
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(callback.from_user.id)
        user.timezone = tz
        await session.commit()
        await session.refresh(user)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Часовой пояс установлен: <b>{tz}</b>",
        reply_markup=settings_keyboard(user),
    )
    await callback.answer()


@router.message(SetTimezoneFSM.waiting_for_tz)
async def set_timezone_from_text(message: Message, state: FSMContext):
    tz = message.text.strip()
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(tz)
    except Exception:
        await message.answer(f"Неверный часовой пояс: <code>{tz}</code>. Попробуй ещё раз.")
        return

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
        user.timezone = tz
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Часовой пояс установлен: <b>{tz}</b>")


# ─── AI Model ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings:ai_model")
async def show_ai_model_selector(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    for model_id, model_label in AI_MODELS:
        builder.row(InlineKeyboardButton(
            text=model_label,
            callback_data=f"settings:ai_set:{model_id}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="settings:menu"))
    await callback.message.edit_text(
        "🤖 <b>Выбери AI модель</b>\n\n"
        "Модель используется для распознавания задач из текста.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:ai_set:"))
async def set_ai_model(callback: CallbackQuery):
    model = callback.data.split(":")[2]
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(callback.from_user.id)
        user.ai_model = model
        await session.commit()
        await session.refresh(user)
    await callback.message.edit_text(
        f"✅ AI модель установлена: <b>{model}</b>",
        reply_markup=settings_keyboard(user),
    )
    await callback.answer("Модель обновлена")
