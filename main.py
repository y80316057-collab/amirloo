import asyncio
import contextlib
import logging
import os
import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Iterable, List, Optional

from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import Message

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency
    genai = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


PROMPT = (
    "Read the numbers in the image from left to right. "
    "Return them as a space-separated list of digits only."
)


@dataclass
class BotState:
    target_chat_id: Optional[int] = None
    spam_task: Optional[asyncio.Task] = None
    is_running: bool = False
    last_numbers: List[str] = field(default_factory=list)


state = BotState()


def _configure_gemini() -> Optional["genai.GenerativeModel"]:
    if genai is None:
        logger.warning("google-generativeai is not installed; OCR will be disabled.")
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set; OCR will be disabled.")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


model = _configure_gemini()


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+", text)


async def _resolve_chat(client: Client, chat_id: int) -> Optional[int]:
    try:
        chat = await client.get_chat(chat_id)
        return chat.id
    except PeerIdInvalid:
        logger.exception("Failed to resolve chat via get_chat.")
        return None


async def _spam_loop(client: Client) -> None:
    while state.is_running and state.target_chat_id is not None:
        resolved = await _resolve_chat(client, state.target_chat_id)
        if resolved is None:
            await asyncio.sleep(2)
            continue
        try:
            await client.send_message(resolved, "Hello")
        except PeerIdInvalid:
            logger.exception("PeerIdInvalid while sending spam message.")
        await asyncio.sleep(2)


def _iter_buttons(message: Message) -> Iterable[tuple[int, int, str]]:
    if not message.reply_markup or not message.reply_markup.inline_keyboard:
        return []
    for row_index, row in enumerate(message.reply_markup.inline_keyboard):
        for col_index, button in enumerate(row):
            if button.text:
                yield row_index, col_index, button.text


async def _auto_click_numbers(message: Message, numbers: List[str]) -> None:
    if not numbers:
        return
    remaining = numbers.copy()
    for row_index, col_index, text in _iter_buttons(message):
        if not remaining:
            break
        expected = remaining[0]
        if text.strip() == expected:
            await message.click(row_index, col_index)
            remaining.pop(0)


async def _read_numbers_from_photo(message: Message) -> List[str]:
    if model is None:
        return []
    bio = BytesIO()
    await message.download(file_name=bio)
    bio.seek(0)
    response = model.generate_content([PROMPT, bio.getvalue()])
    numbers = _extract_numbers(getattr(response, "text", ""))
    return numbers


app = Client(
    "selfbot",
    api_id=33443313,
    api_hash="d72e1b4c054241bb7d4cc269210f22b0",
)


@app.on_message(filters.command("start", prefixes=".") & filters.me)
async def start_handler(client: Client, message: Message) -> None:
    resolved = await _resolve_chat(client, message.chat.id)
    if resolved is None:
        await message.reply_text("Unable to resolve this chat right now.")
        return
    state.target_chat_id = resolved
    state.is_running = True
    if state.spam_task is None or state.spam_task.done():
        state.spam_task = asyncio.create_task(_spam_loop(client))
    await message.reply_text("Locked onto this group. Spam started.")


@app.on_message(filters.command("stop", prefixes=".") & filters.me)
async def stop_handler(client: Client, message: Message) -> None:
    state.is_running = False
    state.target_chat_id = None
    if state.spam_task and not state.spam_task.done():
        state.spam_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await state.spam_task
    state.spam_task = None
    await message.reply_text("All tasks stopped.")


@app.on_message(filters.photo)
async def photo_handler(client: Client, message: Message) -> None:
    if not state.is_running:
        return
    numbers = await _read_numbers_from_photo(message)
    if numbers:
        state.last_numbers = numbers
        await _auto_click_numbers(message, numbers)


@app.on_message(filters.text)
async def report_handler(client: Client, message: Message) -> None:
    if not state.is_running:
        return
    if message.text and "report" in message.text.lower():
        await client.send_message("me", message.text)


if __name__ == "__main__":
    app.run()
