from __future__ import annotations

from app.services.token_service import (
    CROCKFORD_ALPHABET,
    TOKEN_LENGTH,
    format_token,
    generate_token,
    is_valid_token_format,
    normalize_token,
)


def test_generate_token_has_three_groups_of_four() -> None:
    token = generate_token()
    parts = token.split("-")
    assert len(parts) == 3
    assert all(len(part) == 4 for part in parts)


def test_generate_token_uses_only_crockford_alphabet() -> None:
    token = generate_token()
    cleaned = token.replace("-", "")
    assert len(cleaned) == TOKEN_LENGTH
    assert all(char in CROCKFORD_ALPHABET for char in cleaned)


def test_generate_token_is_unique_across_many_calls() -> None:
    tokens = {generate_token() for _ in range(1000)}
    assert len(tokens) == 1000


def test_normalize_token_is_case_and_hyphen_insensitive() -> None:
    assert normalize_token("k7m2-pq9x-ab43") == "K7M2PQ9XAB43"
    assert normalize_token("K7M2-PQ9X-AB43") == "K7M2PQ9XAB43"
    assert normalize_token("K7M2PQ9XAB43") == "K7M2PQ9XAB43"
    assert normalize_token("  k7m2 pq9x ab43  ") == "K7M2PQ9XAB43"


def test_format_token_inserts_hyphens() -> None:
    assert format_token("K7M2PQ9XAB43") == "K7M2-PQ9X-AB43"
    assert format_token("k7m2pq9xab43") == "K7M2-PQ9X-AB43"


def test_is_valid_token_format_accepts_various_writings() -> None:
    assert is_valid_token_format("K7M2-PQ9X-AB43") is True
    assert is_valid_token_format("k7m2pq9xab43") is True
    assert is_valid_token_format("K7M2PQ9XAB43") is True


def test_is_valid_token_format_rejects_bad_length_or_chars() -> None:
    assert is_valid_token_format("K7M2-PQ9X-AB4") is False  # 11 chars
    assert is_valid_token_format("K7M2-PQ9X-AB433") is False  # 13 chars
    assert is_valid_token_format("I7M2-PQ9X-AB43") is False  # 'I' not in alphabet
    assert is_valid_token_format("O7M2-PQ9X-AB43") is False  # 'O' not in alphabet
    assert is_valid_token_format("") is False