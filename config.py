import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0


EMOJIS = {
    "calculator": "5893161718179173515",
    "premium": "5976721857406048634",
    "sparkle": "5893321843149902412",
    "success": "5895514131896733546",
    "error": "5893163582194978381",
    "admin": "5809838858715535455",
    "stats": "5895444149699612825",
    "users": "5902335789798265487",
    "broadcast": "5893297890117292323",
    "settings": "5902432207519093015",
    "security": "5893365724830765382",
    "bot": "5893161718179173515",
    "info": "5893290369629556374",
    "fire": "5893185207355315979",
    "growth": "5231200819986047254",
    "loading": "5893102202817352158",
    "blocked": "5893401729541608160",
    "delete": "5904542823167824187",
    "back": "5814296854380158492",
}


def custom_emoji(name: str) -> str:
    emoji_id = EMOJIS.get(name)

    if not emoji_id:
        return "✨"

    # Telegram custom emoji HTML
    return f'<tg-emoji emoji-id="{emoji_id}">✨</tg-emoji>'
