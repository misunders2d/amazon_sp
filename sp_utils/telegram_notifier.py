import os

import httpx
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


async def send_telegram_message(message):
    """Send a message to Telegram."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                TELEGRAM_API_URL, json={"chat_id": CHAT_ID, "text": message}
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"Failed to send Telegram notification: {e}")
