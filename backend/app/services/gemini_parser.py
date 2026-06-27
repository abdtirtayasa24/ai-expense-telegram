from datetime import date

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.parser import ParsedTransaction


async def parse_gemini_transaction(text: str, today: date) -> ParsedTransaction:
    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = _build_prompt(text, today)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ParsedTransaction,
        system_instruction=_SYSTEM_INSTRUCTION,
    )

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=config,
    )

    if response.parsed is None:
        raise ValueError("Gemini did not return structured output.")

    parsed: ParsedTransaction = response.parsed
    parsed.parser = "gemini"
    return parsed


def _build_prompt(text: str, today: date) -> str:
    return (
        f"Today date: {today.isoformat()}\n"
        f"Timezone: Asia/Jakarta\n\n"
        f"User message:\n{text}\n\n"
        f"Return JSON according to the schema."
    )


_SYSTEM_INSTRUCTION = (
    "You are an Indonesian-language personal finance transaction parser. "
    "Your only task is to convert the user's message into a structured JSON "
    "transaction object. "
    "You must not provide financial advice, commentary, explanations, "
    "summaries, or any text outside the JSON output. "
    "Always use Indonesian context when interpreting the user's message. "
    "Rules: "
    "The currency must always be \"IDR\". "
    "Use the Asia/Jakarta timezone for all dates. "
    "If the user provides a relative date such as \"hari ini\", \"kemarin\", "
    "or \"besok\", resolve it using the Asia/Jakarta timezone. "
    "If no date is mentioned, use the current date in Asia/Jakarta. "
    "If the transaction amount cannot be found or inferred clearly, set "
    "\"needs_clarification\" to true. "
    "If the transaction type is unclear, set \"needs_clarification\" to true. "
    "If the category is unclear but the transaction itself is valid, use the "
    "category \"lainnya\". "
    "Do not invent missing amounts, dates, merchants, notes, or transaction "
    "types. "
    "Do not include fields that are not defined in the JSON schema. "
    "Output valid JSON only. "
    "Transaction type rules: "
    "Use \"expense\" for money spent, purchases, payments, bills, food, "
    "transport, shopping, and similar outgoing transactions. "
    "Use \"income\" for salary, gifts received, refunds, bonuses, sales "
    "revenue, and similar incoming transactions. "
    "If the type cannot be determined confidently, set "
    "\"needs_clarification\" to true."
)
