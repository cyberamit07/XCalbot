# XCalbot - Telegram Calculator Bot

A production-ready Telegram calculator bot with admin panel, user tracking, and broadcast capabilities.

## Features

- 🔢 **Smart Calculator**: Supports +, -, *, /, %, ^, (), decimals
- 👑 **Admin Panel**: Statistics, User management, Broadcast system
- 📊 **User Tracking**: Automatic user tracking with SQLite
- 📢 **Broadcast System**: Send messages to all users with flood control
- 🎨 **Premium Styling**: Custom emojis and clean formatting
- 🛡️ **Secure**: No eval() usage, safe expression parsing
- ⚡ **Production Ready**: Error handling, logging, health checks

## Tech Stack

- Python 3.11.11
- aiogram 3.4.1
- SQLite
- aiohttp (Health server)
- python-dotenv

## Deployment on Render

### 1. Prepare Repository

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/XCalbot.git
git push -u origin main
