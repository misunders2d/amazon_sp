import requests, os
from dotenv import load_dotenv
load_dotenv()



BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram_message(message):
    """Send a message to Telegram."""
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            json={"chat_id": CHAT_ID, "text": message}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to send Telegram notification: {e}")