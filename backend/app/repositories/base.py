from collections.abc import Mapping
from typing import Any, Protocol

Row = dict[str, Any]
Payload = Mapping[str, Any]


class QueryResult(Protocol):
    data: list[Row] | None


class QueryBuilder(Protocol):
    def select(self, columns: str = "*") -> "QueryBuilder": ...

    def insert(self, json: Payload) -> "QueryBuilder": ...

    def update(self, json: Payload) -> "QueryBuilder": ...

    def delete(self) -> "QueryBuilder": ...

    def eq(self, column: str, value: Any) -> "QueryBuilder": ...

    def gt(self, column: str, value: Any) -> "QueryBuilder": ...

    def gte(self, column: str, value: Any) -> "QueryBuilder": ...

    def lt(self, column: str, value: Any) -> "QueryBuilder": ...

    def order(self, column: str, desc: bool = False) -> "QueryBuilder": ...

    def limit(self, count: int) -> "QueryBuilder": ...

    def range(self, start: int, end: int) -> "QueryBuilder": ...

    def execute(self) -> QueryResult: ...


class RpcBuilder(Protocol):
    def execute(self) -> QueryResult: ...


class SupabaseClient(Protocol):
    def table(self, table_name: str) -> QueryBuilder: ...

    def rpc(self, function_name: str, params: Payload) -> RpcBuilder: ...


class BaseRepository:
    table_name: str

    def __init__(self, client: SupabaseClient | None = None) -> None:
        if client is None:
            from app.integrations.supabase_client import get_supabase

            client = get_supabase()
        self.client = client

    def table(self) -> QueryBuilder:
        return self.client.table(self.table_name)

    @staticmethod
    def first(result: QueryResult) -> Row | None:
        if not result.data:
            return None
        return result.data[0]

    @staticmethod
    def rows(result: QueryResult) -> list[Row]:
        return result.data or []
