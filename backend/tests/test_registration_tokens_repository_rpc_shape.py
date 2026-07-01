from __future__ import annotations

from typing import Any

from app.repositories.registration_tokens_repository import RegistrationTokensRepository
from tests.test_repositories import FakeResult


class ScalarJsonRpcBuilder:
    def execute(self) -> FakeResult:
        return FakeResult({"ok": False, "error": "not_found"})  # type: ignore[arg-type]


class ScalarJsonRpcClient:
    def table(self, table_name: str) -> Any:
        raise AssertionError("table should not be used")

    def rpc(self, function_name: str, params: dict[str, Any]) -> ScalarJsonRpcBuilder:
        assert function_name == "claim_registration_token"
        return ScalarJsonRpcBuilder()


def test_claim_accepts_scalar_json_rpc_response() -> None:
    repository = RegistrationTokensRepository(ScalarJsonRpcClient())  # type: ignore[arg-type]

    result = repository.claim("K7M2-PQ9X-AB43", telegram_user_id=111)

    assert result == {"ok": False, "error": "not_found"}
