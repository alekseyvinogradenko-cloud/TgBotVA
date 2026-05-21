"""Telegram webhook router — one opaque endpoint per bot."""
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, Header

from app.bots.manager import bot_manager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/{webhook_id}")
async def telegram_webhook(
    webhook_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    # Timing-safe secret comparison
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", settings.webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Resolve opaque id → real bot token (token never appears in the URL/logs)
    token = bot_manager.token_for_webhook_id(webhook_id)
    if not token:
        raise HTTPException(status_code=404, detail="Unknown webhook")

    update_data = await request.json()
    try:
        await bot_manager.process_update(token, update_data)
    except Exception as e:
        logger.exception(f"Error processing update: {type(e).__name__}")
    return {"ok": True}
