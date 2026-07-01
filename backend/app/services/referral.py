import random
import string


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
