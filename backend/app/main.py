"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine
from app.db.models import Base
from app.api import webhooks, workspaces, tasks, projects
from app.bots.manager import bot_manager
from app.tasks.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load existing workspaces and register their bots
    from app.db.session import AsyncSessionLocal
    from app.db.models import Workspace
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.is_active == True)
        )
        workspaces_list = result.scalars().all()
        for ws in workspaces_list:
            try:
                await bot_manager.register_bot(ws.telegram_bot_token, str(ws.id))
                logger.info(f"Loaded bot for workspace: {ws.name}")
            except Exception as e:
                logger.error(f"Failed to load bot {ws.name}: {e}")

    setup_scheduler()
    logger.info(f"Loaded {len(workspaces_list)} bots")

    yield

    # Shutdown
    logger.info("Shutting down...")
    for token in bot_manager.get_tokens():
        await bot_manager.unregister_bot(token)
    from app.tasks.scheduler import scheduler
    scheduler.shutdown()


app = FastAPI(
    title="Personal Assistant Bot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(workspaces.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(projects.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "bots": len(bot_manager.get_tokens())}
