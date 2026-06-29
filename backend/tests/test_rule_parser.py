from datetime import date
from decimal import Decimal

from pytest import MonkeyPatch

from app.schemas.parser import ParsedTransaction
from app.services.rule_parser import (
    detect_transaction_date,
    normalize_text,
    parse_amount,
    parse_rule_based_transaction,
)

THRESHOLD = 0.75
TODAY = date(2026, 6, 26)


def assert_confident(result: ParsedTransaction) -> None:
    assert result.needs_clarification is False
    assert result.confidence_score >= THRESHOLD
    assert result.parser == "rule_based"


def test_required_rule_parser_examples() -> None:
    cases = [
        ("Bayar parkir 5000", "expense", "transportasi", Decimal("5000")),
        ("Beli kopi 18rb", "expense", "makanan_minuman", Decimal("18000")),
        ("Makan siang 35000", "expense", "makanan_minuman", Decimal("35000")),
        ("Gaji masuk 8000000", "income", "pendapatan", Decimal("8000000")),
        ("Dapat bonus 1 juta", "income", "pendapatan", Decimal("1000000")),
        ("Bayar listrik Rp250.000", "expense", "tagihan", Decimal("250000")),
    ]

    for text, transaction_type, category, amount in cases:
        result = parse_rule_based_transaction(text, today=TODAY)

        assert_confident(result)
        assert result.type == transaction_type
        assert result.category == category
        assert result.amount == amount
        assert result.transaction_date == TODAY


def test_supported_mvp_examples_parse_with_high_confidence() -> None:
    cases = [
        ("Beli kopi 18000", "expense", "makanan_minuman", Decimal("18000"), TODAY),
        ("Dapat transfer 500000", "income", "pendapatan", Decimal("500000"), TODAY),
        ("Bayar listrik 250000", "expense", "tagihan", Decimal("250000"), TODAY),
        ("Isi bensin 100000", "expense", "transportasi", Decimal("100000"), TODAY),
        (
            "Kemarin bayar parkir 5000",
            "expense",
            "transportasi",
            Decimal("5000"),
            date(2026, 6, 25),
        ),
        (
            "Hari ini beli kopi 18rb",
            "expense",
            "makanan_minuman",
            Decimal("18000"),
            TODAY,
        ),
    ]

    for text, transaction_type, category, amount, transaction_date in cases:
        result = parse_rule_based_transaction(text, today=TODAY)

        assert_confident(result)
        assert result.type == transaction_type
        assert result.category == category
        assert result.amount == amount
        assert result.transaction_date == transaction_date


def test_amount_parser_supports_spec_variants() -> None:
    cases = {
        "5000": Decimal("5000"),
        "5.000": Decimal("5000"),
        "Rp5.000": Decimal("5000"),
        "5k": Decimal("5000"),
        "5rb": Decimal("5000"),
        "50 ribu": Decimal("50000"),
        "1 juta": Decimal("1000000"),
        "1.5 juta": Decimal("1500000"),
        "1,5 juta": Decimal("1500000"),
        "1.500 juta": Decimal("1500000000"),
    }

    for text, amount in cases.items():
        assert parse_amount(text) == amount


def test_parser_uses_jakarta_today_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.rule_parser.today_jakarta",
        lambda: TODAY,
    )

    result = parse_rule_based_transaction("Bayar parkir 5000")

    assert result.transaction_date == TODAY


def test_date_detector_supports_relative_phrases() -> None:
    assert detect_transaction_date("hari ini beli kopi", TODAY) == TODAY
    assert detect_transaction_date("tadi pagi beli kopi", TODAY) == TODAY
    assert detect_transaction_date("tadi siang beli kopi", TODAY) == TODAY
    assert detect_transaction_date("tadi malam beli kopi", TODAY) == TODAY
    assert detect_transaction_date("beli kopi", TODAY) == TODAY
    assert detect_transaction_date("kemarin beli kopi", TODAY) == date(2026, 6, 25)


def test_parser_returns_clarification_for_missing_amount() -> None:
    result = parse_rule_based_transaction("Bayar parkir", today=TODAY)

    assert result.amount is None
    assert result.type == "expense"
    assert result.category == "transportasi"
    assert result.needs_clarification is True
    assert result.confidence_score < THRESHOLD
    assert result.clarification_question == (
        "Nominalnya belum terbaca. Contoh: Bayar parkir 5000 atau Bayar paylater 250rb"
    )


def test_parser_returns_clarification_for_unclear_type() -> None:
    # Use input without category keyword to trigger unclear type
    result = parse_rule_based_transaction("abc 5000", today=TODAY)

    assert result.amount == Decimal("5000")
    assert result.type is None
    assert result.category == "lainnya"
    assert result.needs_clarification is True
    assert result.confidence_score < THRESHOLD
    assert result.clarification_question is not None
    assert "pemasukan atau pengeluaran" in result.clarification_question


def test_parser_normalizes_text() -> None:
    assert normalize_text("  Bayar   Rp. 5.000  ") == "bayar rp 5.000"
