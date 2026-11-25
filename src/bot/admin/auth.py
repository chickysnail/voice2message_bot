"""Who is asking for the dashboard.

Two ways in, both signed with the bot token so nothing extra needs
configuring:
- Telegram Mini App: Telegram signs the `initData` it hands the page.
  https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
- Browser link: `/admin` hands out a short-lived token signed by the bot.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

# Telegram's own advice: don't trust initData older than a day.
INIT_DATA_MAX_AGE_SECONDS = 24 * 3600


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age: int = INIT_DATA_MAX_AGE_SECONDS,
    now: float | None = None,
) -> int | None:
    """Return the Telegram user id from valid Mini App initData, else None."""
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received = fields.pop("hash", None)
    if not received:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        auth_date = int(fields.get("auth_date", "0"))
        user = json.loads(fields.get("user", "{}"))
        user_id = int(user["id"])
    except (ValueError, KeyError, TypeError):
        return None
    if (now if now is not None else time.time()) - auth_date > max_age:
        return None
    return user_id


def _link_signature(payload: str, bot_token: str) -> str:
    key = hashlib.sha256(b"admin-dashboard-link:" + bot_token.encode()).digest()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_link_token(
    user_id: int, bot_token: str, ttl_seconds: int, now: float | None = None
) -> str:
    expires = int((now if now is not None else time.time()) + ttl_seconds)
    payload = f"{user_id}.{expires}"
    return f"{payload}.{_link_signature(payload, bot_token)}"


def validate_link_token(
    token: str, bot_token: str, now: float | None = None
) -> int | None:
    """Return the user id from an unexpired link token, else None."""
    try:
        user_id_s, expires_s, signature = token.split(".")
        user_id, expires = int(user_id_s), int(expires_s)
    except ValueError:
        return None
    expected = _link_signature(f"{user_id_s}.{expires_s}", bot_token)
    if not hmac.compare_digest(expected, signature):
        return None
    if (now if now is not None else time.time()) > expires:
        return None
    return user_id


def authenticate(authorization: str, bot_token: str) -> int | None:
    """Resolve an `Authorization: tma <initData>` or `Link <token>` header."""
    scheme, _, credentials = authorization.partition(" ")
    if scheme == "tma":
        return validate_init_data(credentials, bot_token)
    if scheme == "Link":
        return validate_link_token(credentials, bot_token)
    return None
