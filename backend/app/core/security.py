import hashlib
import hmac
import json
from urllib.parse import unquote, parse_qsl

from backend.app.core.config import settings


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData signature.
    Returns parsed data dict if valid, None if invalid.

    Telegram docs: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    # Build the data-check string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # HMAC-SHA256 with key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Parse the user field
    result = dict(parsed)
    if "user" in result:
        result["user"] = json.loads(unquote(result["user"]))

    return result


def validate_cryptopay_webhook(payload: bytes, signature: str) -> bool:
    """
    Validate incoming CryptoPay webhook signature.
    """
    expected = hmac.new(
        settings.cryptopay_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)