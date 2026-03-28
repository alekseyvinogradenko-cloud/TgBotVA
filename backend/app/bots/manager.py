"""
Multi-bot manager.
Each workspace registers its own Telegram bot token.
All bots share one FastAPI app via webhook routing.
"""
import logging
from typing import Dict

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from app.bots.handlers import register_all_handlers

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self._bots: Dict[str, tuple[Bot, Dispatcher]] = {}

    async def register_bot(self, token: str, workspace_id: str) -> Bot:
        if token in self._bots:
            return self._bots[token][0]

        bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher(storage=MemoryStorage())
        dp["workspace_id"] = workspace_id

        register_all_handlers(dp)

        self._bots[token] = (bot, dp)
        logger.info(f"Registered bot for workspace {workspace_id}")
        return bot

    async def process_update(self, token: str, update_data: dict) -> None:
        if token not in self._bots:
            logger.warning(f"Update for unknown bot token: {token[:10]}...")
            return
        bot, dp = self._bots[token]
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)

    async def set_webhook(self, token: str, webhook_url: str, secret: str) -> None:
        bot, _ = self._bots[token]
        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret,
            drop_pending_updates=True,
        )

    async def delete_webhook(self, token: str) -> None:
        if token in self._bots:
            bot, _ = self._bots[token]
            await bot.delete_webhook()

    async def unregister_bot(self, token: str) -> None:
        if token in self._bots:
            await self.delete_webhook(token)
            bot, _ = self._bots.pop(token)
            await bot.session.close()

    def get_tokens(self) -> list[str]:
        return list(self._bots.keys())


bot_manager = BotManager()
