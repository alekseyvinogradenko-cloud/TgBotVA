from aiogram import Dispatcher
from .start import router as start_router
from .tasks import router as tasks_router
from .projects import router as projects_router
from .settings import router as settings_router


def register_all_handlers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(projects_router)
    dp.include_router(settings_router)
