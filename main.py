import base64
import json
import os

from openai import OpenAI
from pyrogram import Client, filters


API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_NAME = os.environ.get("SESSION_NAME", "selfbot")

if API_ID == 0 or not API_HASH:
    raise SystemExit("Missing API_ID or API_HASH environment variables.")


openai_client = OpenAI(
    base_url="https://api.example.com/v1",
    api_key="your-api-key-here",
)

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

def extract_digits(image_path: str, openai_client) -> str:
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    system_prompt = (
        "Identify all numeric digits in this image and return a JSON array of "
        "objects with keys 'digit' and 'x' (the digit's horizontal position from "
        "left to right). Respond ONLY with valid JSON, no extra text."
    )

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    }
                ],
            },
        ],
    )

    content = response.choices[0].message.content or ""

    digits_with_positions = []
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                digit = str(item.get("digit", ""))
                x_value = item.get("x")
                if len(digit) == 1 and digit.isdigit() and isinstance(
                    x_value, (int, float)
                ):
                    digits_with_positions.append((x_value, digit))
    except json.JSONDecodeError:
        digits_with_positions = []

    if digits_with_positions:
        digits_with_positions.sort(key=lambda entry: entry[0])
        return "".join(digit for _, digit in digits_with_positions)

    return "".join(char for char in content if char.isdigit())


@app.on_message(filters.private & filters.photo)
def handle_photo(client: Client, message) -> None:
    file_path = message.download()
    try:
        digits = extract_digits(file_path, openai_client)
        message.reply_text(digits)
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
