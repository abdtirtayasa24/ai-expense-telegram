#!/usr/bin/env python3
"""Seed a deterministic demo user and transactions.

Usage:
    python scripts/seed_demo_data.py --yes

Loads Supabase credentials from the environment or backend/.env.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

DEMO_TELEGRAM_ID = 8385516843
DEMO_FIRST_NAME = "John"
DEMO_LAST_NAME = "Doe"
DEMO_START = date(2026, 1, 1)

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = ROOT / "backend" / ".env"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(BACKEND_ENV)


def monthly_transactions(year: int, month: int) -> list[dict[str, Any]]:
    month_index = month - 1
    salary = 12_500_000 + (500_000 if month >= 4 else 0)
    side_income = 900_000 + month_index * 75_000
    groceries = 640_000 + month_index * 18_000
    eating_out = 285_000 + month_index * 12_000
    transport = 420_000 + month_index * 15_000
    shopping = 350_000 + month_index * 20_000
    entertainment = 260_000 + month_index * 10_000
    health = 0 if month in {1, 3, 5} else 175_000
    education = 150_000 if month in {2, 5} else 0

    rows = [
        income(1, "Gaji bulanan", salary),
        expense(2, "Sewa apartemen", "tempat_tinggal", 3_200_000),
        expense(3, "Listrik dan air", "tagihan", 520_000 + month_index * 8_000),
        expense(4, "Internet rumah", "tagihan", 350_000),
        expense(5, "Cicilan motor", "utang_cicilan", 875_000),
        expense(6, "Belanja bulanan", "makanan_minuman", groceries),
        expense(8, "Transportasi kerja", "transportasi", transport),
        expense(10, "Makan siang kantor", "makanan_minuman", eating_out),
        expense(
            12,
            "Kopi dan camilan",
            "makanan_minuman",
            145_000 + month_index * 9_000,
        ),
        expense(14, "Belanja kebutuhan pribadi", "belanja", shopping),
        expense(16, "Hiburan akhir pekan", "hiburan", entertainment),
        expense(18, "Kirim uang keluarga", "keluarga", 750_000),
        expense(21, "Obat dan vitamin", "kesehatan", health),
        expense(23, "Kursus online", "pendidikan", education),
        expense(
            25,
            "Parkir dan tol",
            "transportasi",
            185_000 + month_index * 7_000,
        ),
        expense(27, "Lain-lain", "lainnya", 120_000 + month_index * 5_000),
        income(28, "Freelance", side_income),
    ]
    transactions = []
    for row in rows:
        if row["amount"] <= 0:
            continue
        day = row.pop("day")
        transactions.append(
            {
                **row,
                "transaction_date": date(year, month, day).isoformat(),
            }
        )
    return transactions


def income(day: int, name: str, amount: int) -> dict[str, Any]:
    return base_row(day, "income", name, "pendapatan", amount)


def expense(
    day: int,
    name: str,
    category: str,
    amount: int,
) -> dict[str, Any]:
    return base_row(day, "expense", name, category, amount)


def base_row(
    day: int,
    transaction_type: str,
    name: str,
    category: str,
    amount: int,
) -> dict[str, Any]:
    return {
        "day": day,
        "type": transaction_type,
        "name": name,
        "category": category,
        "amount": amount,
        "source": "manual",
        "parser": "manual",
    }


def build_transactions(user_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for month in range(1, 7):
        rows.extend(monthly_transactions(2026, month))
    return [{**row, "user_id": user_id} for row in rows]


def upsert_demo_user(client: Any) -> dict[str, Any]:
    payload = {
        "telegram_user_id": DEMO_TELEGRAM_ID,
        "telegram_username": "demo_john_doe",
        "first_name": DEMO_FIRST_NAME,
        "last_name": DEMO_LAST_NAME,
        "role": "user",
        "status": "active",
        "onboarding_status": "completed",
        "language_code": "id",
        "currency": "IDR",
        "timezone": "Asia/Jakarta",
        "cashflow_period_start_day": 1,
        "registered_by_telegram_id": DEMO_TELEGRAM_ID,
        "registered_at": datetime.now(UTC).isoformat(),
        "unregistered_at": None,
    }
    result = (
        client.table("users")
        .select("*")
        .eq("telegram_user_id", DEMO_TELEGRAM_ID)
        .limit(1)
        .execute()
    )
    if result.data:
        user_id = result.data[0]["id"]
        updated = client.table("users").update(payload).eq("id", user_id).execute()
        return updated.data[0]
    created = client.table("users").insert(payload).execute()
    return created.data[0]


def seed() -> tuple[str, int]:
    load_env()
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

    from supabase import create_client

    client = create_client(supabase_url, service_key)
    user = upsert_demo_user(client)
    user_id = user["id"]
    client.table("transactions").delete().eq("user_id", user_id).gte(
        "transaction_date",
        DEMO_START.isoformat(),
    ).execute()
    transactions = build_transactions(user_id)
    client.table("transactions").insert(transactions).execute()
    return user_id, len(transactions)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="write demo data")
    args = parser.parse_args()

    preview_count = len(build_transactions("preview-user"))
    if not args.yes:
        print(
            f"Would seed {preview_count} transactions "
            f"for John Doe ({DEMO_TELEGRAM_ID})."
        )
        print("Run again with --yes to write to Supabase.")
        return 0

    user_id, count = seed()
    print(
        f"Seeded John Doe ({DEMO_TELEGRAM_ID}) as {user_id} "
        f"with {count} transactions."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
