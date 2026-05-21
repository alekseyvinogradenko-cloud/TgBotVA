"""
Security helpers — Telegram initData verification and JWT issuance for the Mini App.

initData verification follows the official Telegram WebApp spec:
  https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl

from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24  # short-lived; membership is re-checked per request anyway
INIT_DATA_MAX_AGE_SECONDS = 24 * 60 * 60  # reject initData older than 24h (replay protection)


def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Verify the HMAC signature of a Telegram WebApp initData string.

    Returns parsed fields (dict) on success, None on any failure.
    The returned dict has 'user' as a JSON string — caller should json.loads it.
    """
    if not init_data or not bot_token:
        return None

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    # Build data_check_string: sort by key, join "k=v" lines with \n
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Replay protection — auth_date is mandatory (a forged blob omitting it
    # must not bypass the freshness window)
    auth_date = parsed.get("auth_date")
    if not auth_date:
        return None
    try:
        age = datetime.now(timezone.utc).timestamp() - int(auth_date)
        if age > INIT_DATA_MAX_AGE_SECONDS:
            logger.warning(f"initData rejected — too old ({age:.0f}s)")
            return None
    except ValueError:
        return None

    return parsed


def parse_init_data_user(verified_parsed: dict) -> Optional[dict]:
    """Extract and parse the 'user' JSON blob from verified initData fields."""
    user_raw = verified_parsed.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None


def create_access_token(user_id: str, workspace_id: str) -> str:
    """Create a signed JWT for a Mini App session."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "ws": str(workspace_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload on success, None otherwise."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
