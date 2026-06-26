from typing import Any, Protocol

from app.bot import responses
from app.repositories.base import Row
from app.repositories.users_repository import UsersRepository


class TelegramMessageSender(Protocol):
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> Any: ...


async def handle_admin_command(
    text: str,
    sender_telegram_user_id: int,
    chat_id: int,
    admin_telegram_id: int,
    users_repository: UsersRepository,
    telegram_client: TelegramMessageSender,
) -> bool:
    command, args = _parse_command(text)
    if command not in {"/register", "/unreg", "/users"}:
        return False

    if sender_telegram_user_id != admin_telegram_id:
        await telegram_client.send_message(chat_id, responses.ACCESS_DENIED)
        return True

    if command == "/register":
        await _handle_register(
            args,
            chat_id,
            admin_telegram_id,
            users_repository,
            telegram_client,
        )
        return True

    if command == "/unreg":
        await _handle_unregister(
            args,
            chat_id,
            admin_telegram_id,
            users_repository,
            telegram_client,
        )
        return True

    await _handle_users(chat_id, users_repository, telegram_client)
    return True


async def _handle_register(
    args: list[str],
    chat_id: int,
    admin_telegram_id: int,
    users_repository: UsersRepository,
    telegram_client: TelegramMessageSender,
) -> None:
    target_id = _parse_telegram_id(args, responses.INVALID_REGISTER_USAGE)
    if isinstance(target_id, str):
        await telegram_client.send_message(chat_id, target_id)
        return

    existing_user = users_repository.get_by_telegram_user_id(target_id)
    if existing_user is None:
        users_repository.create_registered_user(
            telegram_user_id=target_id,
            registered_by_telegram_id=admin_telegram_id,
        )
        await telegram_client.send_message(chat_id, responses.USER_REGISTERED)
        return

    if existing_user.get("status") == "inactive":
        reset_onboarding = not existing_user.get("first_name") or not existing_user.get(
            "last_name"
        )
        users_repository.reactivate(
            telegram_user_id=target_id,
            registered_by_telegram_id=admin_telegram_id,
            reset_onboarding=reset_onboarding,
        )
        await telegram_client.send_message(chat_id, responses.USER_REACTIVATED)
        return

    await telegram_client.send_message(chat_id, responses.USER_ALREADY_ACTIVE)


async def _handle_unregister(
    args: list[str],
    chat_id: int,
    admin_telegram_id: int,
    users_repository: UsersRepository,
    telegram_client: TelegramMessageSender,
) -> None:
    target_id = _parse_telegram_id(args, responses.INVALID_UNREGISTER_USAGE)
    if isinstance(target_id, str):
        await telegram_client.send_message(chat_id, target_id)
        return

    if target_id == admin_telegram_id:
        await telegram_client.send_message(
            chat_id,
            responses.ADMIN_SELF_UNREGISTER_DENIED,
        )
        return

    existing_user = users_repository.get_by_telegram_user_id(target_id)
    if existing_user is None:
        await telegram_client.send_message(chat_id, responses.USER_NOT_REGISTERED)
        return

    if existing_user.get("status") == "inactive":
        await telegram_client.send_message(chat_id, responses.USER_ALREADY_INACTIVE)
        return

    users_repository.deactivate(target_id)
    await telegram_client.send_message(chat_id, responses.USER_UNREGISTERED)


async def _handle_users(
    chat_id: int,
    users_repository: UsersRepository,
    telegram_client: TelegramMessageSender,
) -> None:
    users = users_repository.list_users()
    if not users:
        await telegram_client.send_message(chat_id, responses.NO_REGISTERED_USERS)
        return

    lines = ["Daftar user terdaftar:", ""]
    for index, user in enumerate(users, start=1):
        telegram_user_id = user["telegram_user_id"]
        display_name = _format_display_name(user)
        status = user["status"]
        lines.append(f"{index}. {telegram_user_id} - {display_name} - {status}")

    await telegram_client.send_message(chat_id, "\n".join(lines))


def _parse_command(text: str) -> tuple[str, list[str]]:
    parts = text.strip().split()
    if not parts:
        return "", []
    command = parts[0].split("@", maxsplit=1)[0].lower()
    return command, parts[1:]


def _parse_telegram_id(args: list[str], usage_message: str) -> int | str:
    if len(args) != 1:
        return usage_message
    try:
        telegram_user_id = int(args[0])
    except ValueError:
        return responses.INVALID_TELEGRAM_ID
    if telegram_user_id <= 0:
        return responses.INVALID_TELEGRAM_ID
    return telegram_user_id


def _format_display_name(user: Row) -> str:
    first_name = (user.get("first_name") or "").strip()
    last_name = (user.get("last_name") or "").strip()
    full_name = " ".join(part for part in [first_name, last_name] if part)
    return full_name or "Belum isi nama"
