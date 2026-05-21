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
from aiogram.types import MenuButtonWebApp, Update, WebAppInfo

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
        # drop_pending_updates=False: keep updates queued during a redeploy so
        # the new instance picks them up instead of losing them.
        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret,
            drop_pending_updates=False,
        )

    async def delete_webhook(self, token: str) -> None:
        if token in self._bots:
            bot, _ = self._bots[token]
            await bot.delete_webhook()

    async def send_message(self, token: str, chat_id: int, text: str) -> bool:
        """Send an HTML message via the given bot. Returns False if bot is
        not registered or Telegram rejects (e.g. user never /started the bot)."""
        if token not in self._bots:
            logger.warning("send_message: bot not registered")
            return False
        bot, _ = self._bots[token]
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return True
        except Exception as e:
            logger.warning(f"send_message failed: {e}")
            return False

    async def set_menu_button(self, token: str, text: str, url: str) -> None:
        """Pin the 'Open Mini App' button to the bottom-left of every chat with this bot.

        Persists on Telegram side — set once per deploy, shows for all users.
        """
        bot, _ = self._bots[token]
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text=text, web_app=WebAppInfo(url=url)),
        )

    async def unregister_bot(self, token: str) -> None:
        # Intentionally do NOT call delete_webhook here. Render redeploys
        # shut down the old container and bring up a new one within seconds;
        # if we drop the webhook on Telegram side, the new container has to
        # re-register it on startup. That re-registration was failing silently
        # (rate-limit / transient network), leaving the bot unreachable until
        # someone re-set the webhook manually. Keeping the same URL means
        # Telegram just retries delivery to the next-live instance.
        if token in self._bots:
            bot, _ = self._bots.pop(token)
            await bot.session.close()

    def get_tokens(self) -> list[str]:
        return list(self._bots.keys())


bot_manager = BotManager()
