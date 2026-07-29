import re

from backend.app.services.referral import generate_promo_code, generate_wallet_id

VALID_CHARS = re.compile(r"^[A-Z0-9]+$")


def test_wallet_id_format():
    wallet_id = generate_wallet_id()
    assert len(wallet_id) == 16
    assert VALID_CHARS.match(wallet_id)


def test_wallet_id_is_effectively_unique():
    ids = {generate_wallet_id() for _ in range(500)}
    assert len(ids) == 500


def test_promo_code_format():
    code = generate_promo_code()
    assert len(code) == 8
    assert VALID_CHARS.match(code)


def test_promo_code_is_effectively_unique():
    codes = {generate_promo_code() for _ in range(500)}
    assert len(codes) == 500
