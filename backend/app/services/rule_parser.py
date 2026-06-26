import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.schemas.parser import ParsedTransaction, TransactionCategory, TransactionType
from app.services.transaction_categories import CATEGORY_KEYWORDS

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")
PARSER_NAME = "rule_based"

INCOME_SIGNALS: tuple[str, ...] = (
    "transfer masuk",
    "gaji",
    "masuk",
    "dapat",
    "terima",
    "bonus",
    "freelance",
    "pendapatan",
)
EXPENSE_SIGNALS: tuple[str, ...] = (
    "transfer ke",
    "bayar",
    "beli",
    "jajan",
    "makan",
    "isi",
    "topup",
    "keluar",
    "habis",
    "buat",
)
TODAY_PHRASES: tuple[str, ...] = (
    "hari ini",
    "tadi pagi",
    "tadi siang",
    "tadi malam",
)
DATE_PHRASES: tuple[str, ...] = ("kemarin", *TODAY_PHRASES)
AMOUNT_PATTERN = re.compile(
    r"(?P<amount>(?:rp\s*)?\d+(?:[\.,]\d+)*)(?:\s*(?P<suffix>juta|ribu|rb|k))?",
    re.IGNORECASE,
)
WHITESPACE_PATTERN = re.compile(r"\s+")


def parse_rule_based_transaction(
    text: str,
    today: date | None = None,
) -> ParsedTransaction:
    normalized_text = normalize_text(text)
    reference_date = today or today_jakarta()
    transaction_date = detect_transaction_date(normalized_text, reference_date)
    amount = parse_amount(normalized_text)
    transaction_type = detect_transaction_type(normalized_text)
    category = detect_category(normalized_text, transaction_type)
    name = extract_name(normalized_text)
    needs_clarification, clarification_question = build_clarification(
        amount,
        transaction_type,
    )
    confidence_score = score_confidence(
        amount=amount,
        transaction_type=transaction_type,
        category=category,
        name=name,
        needs_clarification=needs_clarification,
    )

    return ParsedTransaction(
        name=name or "Transaksi",
        amount=amount,
        type=transaction_type,
        category=category,
        transaction_date=transaction_date,
        parser=PARSER_NAME,
        confidence_score=confidence_score,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
    )


def normalize_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = normalized.replace("rp.", "rp")
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized


def today_jakarta() -> date:
    return datetime.now(JAKARTA_TZ).date()


def detect_transaction_date(text: str, today: date | None = None) -> date:
    reference_date = today or today_jakarta()
    if "kemarin" in text:
        return reference_date - timedelta(days=1)
    return reference_date


def parse_amount(text: str) -> Decimal | None:
    match = AMOUNT_PATTERN.search(text)
    if match is None:
        return None

    raw_amount = match.group("amount")
    suffix = (match.group("suffix") or "").lower()
    amount_text = raw_amount.lower().replace("rp", "").strip()

    try:
        if suffix == "juta":
            value = parse_suffixed_amount(amount_text) * Decimal("1000000")
        elif suffix in {"k", "rb", "ribu"}:
            value = Decimal(amount_text.replace(".", "").replace(",", "."))
            value *= Decimal("1000")
        else:
            value = Decimal(re.sub(r"\D", "", amount_text))
    except (InvalidOperation, ValueError):
        return None

    if value <= 0:
        return None
    return value.quantize(Decimal("1"))


def parse_suffixed_amount(amount_text: str) -> Decimal:
    if "." not in amount_text and "," not in amount_text:
        return Decimal(amount_text)

    separators = amount_text.count(".") + amount_text.count(",")
    separator = "." if "." in amount_text else ","
    whole, fraction = amount_text.split(separator, maxsplit=1)
    if separators == 1 and len(fraction) <= 2:
        return Decimal(f"{whole}.{fraction}")
    return Decimal(re.sub(r"\D", "", amount_text))


def detect_transaction_type(text: str) -> TransactionType | None:
    if any(signal in text for signal in INCOME_SIGNALS):
        return "income"
    if any(signal in text for signal in EXPENSE_SIGNALS):
        return "expense"
    return None


def detect_category(
    text: str,
    transaction_type: TransactionType | None,
) -> TransactionCategory:
    if transaction_type == "income":
        return "pendapatan"

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "lainnya"


def extract_name(text: str) -> str:
    name = text
    for phrase in DATE_PHRASES:
        name = name.replace(phrase, " ")
    amount_match = AMOUNT_PATTERN.search(name)
    if amount_match is not None:
        name = f"{name[: amount_match.start()]} {name[amount_match.end() :]}"
    for signal in (*INCOME_SIGNALS, *EXPENSE_SIGNALS):
        name = re.sub(rf"\b{re.escape(signal)}\b", " ", name)
    name = WHITESPACE_PATTERN.sub(" ", name).strip(" -")
    return name.title()


def build_clarification(
    amount: Decimal | None,
    transaction_type: TransactionType | None,
) -> tuple[bool, str | None]:
    if amount is None:
        return True, "Nominalnya belum terbaca. Contoh: Bayar parkir 5000"
    if transaction_type is None:
        return (
            True,
            "Aku belum yakin ini pemasukan atau pengeluaran. "
            "Contoh: Bayar parkir 5000 atau Gaji masuk 8000000",
        )
    return False, None


def score_confidence(
    amount: Decimal | None,
    transaction_type: TransactionType | None,
    category: TransactionCategory,
    name: str,
    needs_clarification: bool,
) -> float:
    score = Decimal("0")
    if amount is not None:
        score += Decimal("0.35")
    if transaction_type is not None:
        score += Decimal("0.30")
    if category != "lainnya":
        score += Decimal("0.20")
    else:
        score += Decimal("0.10")
    if name:
        score += Decimal("0.10")
    score += Decimal("0.05")
    if needs_clarification:
        score = min(score, Decimal("0.60"))
    return float(min(score, Decimal("1.00")))
