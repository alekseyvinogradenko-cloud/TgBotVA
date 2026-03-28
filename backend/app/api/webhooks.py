"""Telegram webhook router — one endpoint per bot token."""
import logging

from fastapi import APIRouter, HTTPException, Request, Header

from app.bots.manager import bot_manager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/{bot_token}")
async def telegram_webhook(
    bot_token: str,
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    update_data = await request.json()
    try:
        await bot_manager.process_update(bot_token, update_data)
    except Exception as e:
        logger.exception(f"Error processing update: {e}")
    return {"ok": True}
