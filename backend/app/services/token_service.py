from __future__ import annotations

import secrets

CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TOKEN_LENGTH = 12
TOKEN_GROUP_SIZE = 4


def generate_token() -> str:
    """Generate a cryptographically secure token in ``XXXX-XXXX-XXXX`` format.

    Uses the Crockford Base32 alphabet (excludes ``I``, ``L``, ``O``, ``U``)
    so tokens stay readable and unambiguous when typed manually in Telegram.
    """
    raw = "".join(secrets.choice(CROCKFORD_ALPHABET) for _ in range(TOKEN_LENGTH))
    return format_token(raw)


def normalize_token(raw: str) -> str:
    """Normalize user-supplied token text for case- and hyphen-insensitive comparison.

    Strips hyphens, spaces, and lowercases to uppercase so that ``k7m2-pq9x-ab43``,
    ``K7M2-PQ9X-AB43``, and ``K7M2PQ9XAB43`` all map to the same canonical form.
    """
    cleaned = raw.strip().upper().replace("-", "").replace(" ", "")
    return cleaned


def format_token(raw: str) -> str:
    """Insert hyphen separators into a 12-char canonical token for display/storage."""
    cleaned = normalize_token(raw)
    return "-".join(
        cleaned[i : i + TOKEN_GROUP_SIZE]
        for i in range(0, len(cleaned), TOKEN_GROUP_SIZE)
    )


def is_valid_token_format(raw: str) -> bool:
    """Return ``True`` when *raw* normalizes to exactly 12 Crockford Base32 chars."""
    cleaned = normalize_token(raw)
    if len(cleaned) != TOKEN_LENGTH:
        return False
    return all(char in CROCKFORD_ALPHABET for char in cleaned)