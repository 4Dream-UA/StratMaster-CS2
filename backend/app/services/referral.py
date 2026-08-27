import random
import secrets
import string


def generate_share_token() -> str:
    """
    Generate a URL-safe token for a public board share link — uses `secrets`
    (not `random`) since, unlike a wallet ID or promo code that a person
    types in by hand, this is pasted/clicked and needs to resist guessing.
    """
    return secrets.token_urlsafe(12)


def generate_wallet_id() -> str:
    """
    Generate a unique 16-character alphanumeric wallet ID.
    Format: Uppercase letters and digits only.
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=16))


def generate_promo_code() -> str:
    """
    Generate a unique promo code.
    Format: Uppercase letters and digits, 8 characters.
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=8))
