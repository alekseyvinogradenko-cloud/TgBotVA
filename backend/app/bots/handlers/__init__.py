import logging
from aiogram import Dispatcher
from aiogram.types import ErrorEvent
from .start import router as start_router
from .tasks import router as tasks_router
from .projects import router as projects_router
from .settings import router as settings_router

logger = logging.getLogger(__name__)


def register_all_handlers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(projects_router)
    dp.include_router(settings_router)

    @dp.errors()
    async def error_handler(event: ErrorEvent) -> bool:
        logger.exception(f"Handler error: {event.exception}", exc_info=event.exception)
        try:
            if event.update.message:
                await event.update.message.answer("⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start")
            elif event.update.callback_query:
                await event.update.callback_query.message.answer("⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start")
                await event.update.callback_query.answer()
        except Exception:
            pass
        return True
