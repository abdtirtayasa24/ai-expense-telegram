from datetime import date

from google import genai
from google.genai import types

from app.core.config import settings
from app.prompts.loader import load_prompt
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


_SYSTEM_INSTRUCTION = load_prompt("gemini_transaction_parser.md")
