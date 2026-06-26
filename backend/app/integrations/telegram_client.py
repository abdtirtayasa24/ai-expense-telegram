import httpx


class TelegramClient:
    def __init__(self, bot_token: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None):
        payload = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
            return response.json()