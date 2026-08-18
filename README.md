# XCalbot

Telegram calculator bot built with Python and aiogram.

## Files

- `bot.py` — Telegram bot handlers and calculator logic
- `config.py` — environment-based configuration
- `database.py` — SQLite user database
- `requirements.txt` — Python dependencies
- `python-version` — Python version used by the project
- `render.yaml` — Render Background Worker configuration
- `Procfile` — worker start command for compatible hosting platforms
- `.python-version` — Python runtime version for compatible hosting platforms
- `.env.example` — required environment variable names

## GitHub

Upload all files in this folder to the root of your GitHub repository.

## Render

Create a **Background Worker** from the repository. Render can use `render.yaml`, or use:

- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`

Add these environment variables in Render:

- `BOT_TOKEN` — your Telegram bot token
- `ADMIN_ID` — your numeric Telegram user ID

Do not commit real tokens or passwords to GitHub.
