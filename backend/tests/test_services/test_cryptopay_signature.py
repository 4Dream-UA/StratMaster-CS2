import hashlib
import hmac

from backend.app.core.config import settings
from backend.app.core.security import validate_cryptopay_webhook


def _sign(body: bytes) -> str:
    secret_key = hashlib.sha256(settings.cryptopay_token.encode()).digest()
    return hmac.new(secret_key, body, hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted():
    body = b'{"update_type":"invoice_paid","payload":{"invoice_id":123}}'
    assert validate_cryptopay_webhook(body, _sign(body)) is True


def test_tampered_body_is_rejected():
    body = b'{"update_type":"invoice_paid","payload":{"invoice_id":123}}'
    signature = _sign(body)
    tampered = body.replace(b"123", b"999")
    assert validate_cryptopay_webhook(tampered, signature) is False


def test_missing_signature_is_rejected():
    body = b'{"update_type":"invoice_paid"}'
    assert validate_cryptopay_webhook(body, "") is False


def test_garbage_signature_is_rejected():
    body = b'{"update_type":"invoice_paid"}'
    assert validate_cryptopay_webhook(body, "not-a-real-signature") is False
