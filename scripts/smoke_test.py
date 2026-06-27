#!/usr/bin/env python3
"""Production smoke tests for AI Telegram Expense Tracker.

Usage:
    BASE_URL=https://api.example.com python scripts/smoke_test.py

Requires ``requests``::

    pip install requests
"""

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def build_init_data(bot_token: str, telegram_user_id: int) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    params = {
        "auth_date": str(now),
        "query_id": "smoke-test",
        "user": json.dumps(
            {"id": telegram_user_id, "first_name": "Smoke"},
            separators=(",", ":"),
        ),
    }
    check = "\n".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    secret = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()
    signature = hmac.new(
        secret, check.encode(), hashlib.sha256
    ).hexdigest()
    encoded = [f"{key}={quote(value)}" for key, value in params.items()]
    encoded.append(f"hash={signature}")
    return "&".join(encoded)


def check(name: str, response: requests.Response, expected_status: int) -> bool:
    ok = response.status_code == expected_status
    status = "✅" if ok else "❌"
    detail = ""
    if not ok:
        try:
            detail = f" (got {response.status_code}, body: {response.text[:200]})"
        except Exception:
            detail = f" (got {response.status_code})"
    print(f"  {status} {name}{detail}")
    return ok


def main() -> int:
    print(f"Smoke testing {BASE_URL}\n")

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "test-token")
    passed = 0
    total = 0

    # 1. Health
    total += 1
    passed += check("GET /health", requests.get(urljoin(BASE_URL, "/health")), 200)

    # 2. Auth
    total += 1
    init_data = build_init_data(bot_token, 111)
    auth_resp = requests.post(
        urljoin(BASE_URL, "/auth/telegram-mini-app"),
        json={"init_data": init_data},
    )
    passed += check("POST /auth/telegram-mini-app", auth_resp, 200)

    token = None
    if auth_resp.status_code == 200:
        token = auth_resp.json().get("access_token")

    if not token:
        print("\n  ⚠️  No JWT — skipping protected endpoint tests.\n")
    else:
        headers = {"Authorization": f"Bearer {token}"}
        for name, path in [
            ("GET /transactions", "/transactions"),
            ("GET /dashboard/summary", "/dashboard/summary"),
            ("GET /budgets", "/budgets?month=2026-06"),
            ("POST /advisor/insights", "/advisor/insights"),
        ]:
            total += 1
            method = requests.post if "POST" in name else requests.get
            json_body = {} if "POST" in name else None
            resp = method(
                urljoin(BASE_URL, path),
                headers=headers,
                json=json_body,
            )
            # Advisor returns 200 with fallback text on error, budget may fail
            # if no user exists; we accept 200, 201, 403, 404
            expected = 200
            if name.startswith("POST /advisor"):
                # Advisor may return 200 even if user has no data
                expected = 200
            passed += check(name, resp, expected)

    print(f"\n{passed}/{total} passed")
    if passed == total:
        print("All smoke tests passed. 🚀")
        return 0
    else:
        print("Some tests failed — review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
