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
    "uang masuk",
    "dana masuk",
    "saldo masuk",
    "masuk rekening",
    "gaji masuk",
    "gajian",
    "gaji",
    "salary",
    "payroll",
    "pemasukan",
    "pendapatan",
    "income",
    "dapat transfer",
    "dapet transfer",
    "dapat",
    "dapet",
    "terima",
    "menerima",
    "diterima",
    "bonus",
    "thr",
    "tunjangan",
    "insentif",
    "komisi",
    "fee freelance",
    "freelance",
    "honorarium",
    "honor",
    "upah",
    "bayaran",
    "hasil jualan",
    "hasil dagang",
    "jualan",
    "profit",
    "refund",
    "reimburse",
    "reimbursement",
    "cashback",
    "dividen",
    "bunga tabungan",
    "uang saku",
    "dikasih",
    "hadiah",
    "cair",
)

EXPENSE_SIGNALS: tuple[str, ...] = (
    "transfer ke",
    "tf ke",
    "kirim ke",
    "bayar",
    "membayar",
    "pembayaran",
    "dibayarkan",
    "beli",
    "membeli",
    "belanja",
    "checkout",
    "check out",
    "co ",
    "jajan",
    "makan pagi",
    "makan siang",
    "makan malam",
    "sarapan",
    "makan",
    "minum",
    "ngopi",
    "isi",
    "isi ulang",
    "top up",
    "topup",
    "keluar",
    "pengeluaran",
    "habis",
    "kepakai",
    "terpakai",
    "pakai",
    "buat",
    "untuk",
    "biaya",
    "ongkos",
    "tarif",
    "tagihan",
    "cicilan",
    "angsuran",
    "paylater",
    "spaylater",
    "gopaylater",
    "pinjol",
    "langganan",
    "subscribe",
    "perpanjang",
    "perpanjangan",
    "patungan",
    "donasi",
    "sedekah",
    "zakat",
)

YESTERDAY_PHRASES: tuple[str, ...] = (
    "kemarin",
    "kemaren",
    "kmrn",
    "semalam",
)
TODAY_PHRASES: tuple[str, ...] = (
    "hari ini",
    "hr ini",
    "barusan",
    "tadi",
    "tadi pagi",
    "tadi siang",
    "tadi sore",
    "tadi malam",
    "tadi malem",
    "pagi ini",
    "siang ini",
    "sore ini",
    "malam ini",
    "malem ini",
)
DATE_PHRASES: tuple[str, ...] = (*YESTERDAY_PHRASES, *TODAY_PHRASES)

AMOUNT_PATTERN = re.compile(
    r"(?P<prefix>\brp\.?\s*|\bidr\s*)?"
    r"(?P<amount>\d+(?:[\.,]\d+)*)"
    r"(?:\s*(?P<suffix>juta|jt|mio|miliar|milyar|ribu|rb|rebu|k))?\b",
    re.IGNORECASE,
)
RELATIVE_DAYS_PATTERN = re.compile(
    r"\b(?P<days>\d{1,3})\s*(?:hari|hr)\s*(?:yang\s*)?lalu\b",
    re.IGNORECASE,
)
DATE_NUMBER_PATTERN = re.compile(
    r"\b(?:tgl|tanggal)\s*(?P<day>\d{1,2})"
    r"(?:[\/\-.](?P<month>\d{1,2}))?"
    r"(?:[\/\-.](?P<year>\d{2,4}))?\b",
    re.IGNORECASE,
)
SLASH_DATE_PATTERN = re.compile(
    r"\b(?P<day>\d{1,2})[\/\-](?P<month>\d{1,2})(?:[\/\-](?P<year>\d{2,4}))?\b"
)
WHITESPACE_PATTERN = re.compile(r"\s+")

SLANG_AMOUNT_VALUES: dict[str, Decimal] = {
    "seceng": Decimal("1000"),
    "seribu": Decimal("1000"),
    "goceng": Decimal("5000"),
    "lima ribu": Decimal("5000"),
    "ceban": Decimal("10000"),
    "sepuluh ribu": Decimal("10000"),
    "noban": Decimal("20000"),
    "dua puluh ribu": Decimal("20000"),
    "gocap": Decimal("50000"),
    "goban": Decimal("50000"),
    "lima puluh ribu": Decimal("50000"),
    "cepek": Decimal("100000"),
    "seratus ribu": Decimal("100000"),
    "gopek": Decimal("500000"),
    "lima ratus ribu": Decimal("500000"),
    "sejuta": Decimal("1000000"),
    "satu juta": Decimal("1000000"),
    "setengah juta": Decimal("500000"),
}
SLANG_AMOUNT_PATTERN = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(re.escape(phrase) for phrase in sorted(SLANG_AMOUNT_VALUES, key=len, reverse=True))
    + r")(?![a-z0-9])",
    re.IGNORECASE,
)

CATEGORY_PRIORITY: tuple[TransactionCategory, ...] = (
    "utang_cicilan",
    "tagihan",
    "transportasi",
    "kesehatan",
    "pendidikan",
    "tempat_tinggal",
    "makanan_minuman",
    "belanja",
    "hiburan",
    "keluarga",
    "pendapatan",
    "lainnya",
)


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
    normalized = normalized.replace("rp.", "rp ")
    normalized = normalized.replace("idr.", "idr ")
    normalized = normalized.replace("pay later", "paylater")
    normalized = normalized.replace("spay later", "spaylater")
    normalized = normalized.replace("go paylater", "gopaylater")
    normalized = re.sub(r"\bqris\b", " qris ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized


def today_jakarta() -> date:
    return datetime.now(JAKARTA_TZ).date()


def detect_transaction_date(text: str, today: date | None = None) -> date:
    reference_date = today or today_jakarta()

    explicit_date = parse_explicit_date(text, reference_date)
    if explicit_date is not None:
        return explicit_date

    relative_days = RELATIVE_DAYS_PATTERN.search(text)
    if relative_days is not None:
        return reference_date - timedelta(days=int(relative_days.group("days")))

    if any(phrase in text for phrase in YESTERDAY_PHRASES):
        return reference_date - timedelta(days=1)

    if "minggu lalu" in text or "pekan lalu" in text:
        return reference_date - timedelta(days=7)

    return reference_date


def parse_explicit_date(text: str, reference_date: date) -> date | None:
    for pattern in (DATE_NUMBER_PATTERN, SLASH_DATE_PATTERN):
        match = pattern.search(text)
        if match is None:
            continue

        day = int(match.group("day"))
        month = int(match.group("month") or reference_date.month)
        year_text = match.group("year")
        year = int(year_text) if year_text else reference_date.year
        if year < 100:
            year += 2000

        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None


def parse_amount(text: str) -> Decimal | None:
    amount_candidate = find_amount_candidate(text)
    if amount_candidate is None:
        return None

    value = amount_candidate[0]
    if value <= 0:
        return None
    return value.quantize(Decimal("1"))


def find_amount_candidate(text: str) -> tuple[Decimal, int, int] | None:
    candidates: list[tuple[int, int, Decimal, int, int]] = []

    for match in AMOUNT_PATTERN.finditer(text):
        if is_probably_date_number(text, match):
            continue

        value = parse_numeric_amount(
            amount_text=match.group("amount"),
            prefix=match.group("prefix") or "",
            suffix=match.group("suffix") or "",
        )
        if value is None:
            continue

        score = score_amount_candidate(match)
        candidates.append((score, -match.start(), value, match.start(), match.end()))

    for match in SLANG_AMOUNT_PATTERN.finditer(text):
        value = SLANG_AMOUNT_VALUES[match.group(1).lower()]
        candidates.append((5, -match.start(), value, match.start(), match.end()))

    if not candidates:
        return None

    _, _, value, start, end = max(candidates)
    return value, start, end


def score_amount_candidate(match: re.Match[str]) -> int:
    prefix = match.group("prefix") or ""
    suffix = match.group("suffix") or ""
    digits = re.sub(r"\D", "", match.group("amount"))

    score = 1
    if prefix:
        score += 3
    if suffix:
        score += 4
    if len(digits) >= 4:
        score += 2
    return score


def parse_numeric_amount(
    amount_text: str,
    prefix: str = "",
    suffix: str = "",
) -> Decimal | None:
    amount_text = amount_text.strip()
    suffix = suffix.lower().strip()

    try:
        base_value = parse_decimal_number(amount_text, force_decimal=bool(suffix))
        if suffix in {"juta", "jt", "mio"}:
            base_value *= Decimal("1000000")
        elif suffix in {"miliar", "milyar"}:
            base_value *= Decimal("1000000000")
        elif suffix in {"k", "rb", "ribu", "rebu"}:
            base_value *= Decimal("1000")
        elif not suffix and not prefix and base_value < 0:
            return None
    except (InvalidOperation, ValueError):
        return None

    return base_value


def parse_decimal_number(amount_text: str, force_decimal: bool = False) -> Decimal:
    amount_text = amount_text.replace(" ", "")
    separators = amount_text.count(".") + amount_text.count(",")

    if separators == 0:
        return Decimal(amount_text)

    last_separator_index = max(amount_text.rfind("."), amount_text.rfind(","))
    fraction = amount_text[last_separator_index + 1 :]

    if force_decimal and separators == 1 and len(fraction) <= 2:
        decimal_text = amount_text.replace(",", ".")
        return Decimal(decimal_text)

    if force_decimal and separators > 1 and len(fraction) <= 2:
        whole = re.sub(r"\D", "", amount_text[:last_separator_index])
        return Decimal(f"{whole}.{fraction}")

    return Decimal(re.sub(r"\D", "", amount_text))


def is_probably_date_number(text: str, match: re.Match[str]) -> bool:
    start, end = match.span()
    before = text[max(0, start - 12) : start]
    after = text[end : min(len(text), end + 16)]

    if (start > 0 and text[start - 1] in {"/", "-"}) or (end < len(text) and text[end : end + 1] in {"/", "-"}):
        return True

    if re.search(r"(?:tgl|tanggal)\s*$", before):
        return True

    if re.match(r"\s*(?:hari|hr)\s*(?:yang\s*)?lalu\b", after):
        return True

    return False


def detect_transaction_type(text: str) -> TransactionType | None:
    income_matches = collect_signal_matches(text, INCOME_SIGNALS)
    expense_matches = collect_signal_matches(text, EXPENSE_SIGNALS)

    income_score = sum(score_signal(signal) for signal, _ in income_matches)
    expense_score = sum(score_signal(signal) for signal, _ in expense_matches)

    if expense_score > income_score:
        return "expense"
    if income_score > expense_score:
        return "income"

    if income_matches and expense_matches:
        first_income_pos = min(position for _, position in income_matches)
        first_expense_pos = min(position for _, position in expense_matches)
        return "income" if first_income_pos < first_expense_pos else "expense"

    if income_matches:
        return "income"
    if expense_matches:
        return "expense"

    has_expense_category = any(
        category_match_score(text, category) > 0
        for category in CATEGORY_PRIORITY
        if category not in {"pendapatan", "lainnya"}
    )
    if has_expense_category:
        return "expense"

    return None


def collect_signal_matches(text: str, signals: tuple[str, ...]) -> list[tuple[str, int]]:
    matches: list[tuple[str, int]] = []
    for signal in signals:
        match = find_keyword(text, signal)
        if match is not None:
            matches.append((signal, match.start()))
    return matches


def score_signal(signal: str) -> int:
    score = 1
    if " " in signal:
        score += 1
    if len(signal) >= 8:
        score += 1
    return score


def detect_category(
    text: str,
    transaction_type: TransactionType | None,
) -> TransactionCategory:
    if transaction_type == "income":
        if category_match_score(text, "utang_cicilan") > 0:
            return "utang_cicilan"
        return "pendapatan"

    category_scores: list[tuple[int, int, TransactionCategory]] = []
    for priority_index, category in enumerate(CATEGORY_PRIORITY):
        if category in {"pendapatan", "lainnya"}:
            continue

        score = category_match_score(text, category)
        if score > 0:
            category_scores.append((score, -priority_index, category))

    if not category_scores:
        return "lainnya"

    _, _, category = max(category_scores)
    return category


def category_match_score(text: str, category: TransactionCategory) -> int:
    score = 0
    for keyword in CATEGORY_KEYWORDS.get(category, ()):
        if find_keyword(text, keyword) is None:
            continue
        score += 2
        if " " in keyword:
            score += 2
        if len(keyword) >= 8:
            score += 1
    return score


def find_keyword(text: str, keyword: str) -> re.Match[str] | None:
    keyword = keyword.strip().lower()
    if not keyword:
        return None

    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text)


def extract_name(text: str) -> str:
    name = text

    for pattern in (
        RELATIVE_DAYS_PATTERN,
        DATE_NUMBER_PATTERN,
        SLASH_DATE_PATTERN,
    ):
        name = pattern.sub(" ", name)

    for phrase in sorted(DATE_PHRASES, key=len, reverse=True):
        name = re.sub(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", " ", name)

    amount_candidate = find_amount_candidate(name)
    if amount_candidate is not None:
        _, start, end = amount_candidate
        name = f"{name[:start]} {name[end:]}"

    for signal in sorted((*INCOME_SIGNALS, *EXPENSE_SIGNALS), key=len, reverse=True):
        name = re.sub(rf"(?<![a-z0-9]){re.escape(signal.strip())}(?![a-z0-9])", " ", name)

    name = WHITESPACE_PATTERN.sub(" ", name).strip(" -.,")
    return name.title()


def build_clarification(
    amount: Decimal | None,
    transaction_type: TransactionType | None,
) -> tuple[bool, str | None]:
    if amount is None:
        return True, "Nominalnya belum terbaca. Contoh: Bayar parkir 5000 atau Bayar paylater 250rb"
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
        score += Decimal("0.08")
    if name:
        score += Decimal("0.10")
    score += Decimal("0.05")
    if needs_clarification:
        score = min(score, Decimal("0.60"))
    return float(min(score, Decimal("1.00")))
