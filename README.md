# TelegramStoreBot

## Overview

`TelegramStoreBot` is a full‑featured Telegram bot that manages a multi‑store e‑commerce system. It supports:

- Store creation and management for admins and sellers
- Product catalog with categories and images
- Credit limits and credit‑customer handling
- Order processing, returns, and messaging between buyers and sellers
- Detailed statistics and dashboards

The core logic lives in **`bot.py`**. All database tables are created automatically on first run.

## Prerequisites

- **Python 3.10+** (tested on Windows 10/11)
- Telegram bot token (create a bot via @BotFather)

## Setup

1. **Clone / copy the project** into a folder, e.g. `C:\Users\Hp\Desktop\TelegramStoreBot`.
2. Open a command prompt in that folder.
3. (Optional) Create a virtual environment:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
5. **Configure the token** – you can either:
   - Edit `bot.py` and replace the placeholder token, **or**
   - Set an environment variable `TELEGRAM_BOT_TOKEN`:
     ```bat
     set TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE
     ```

## Running the Bot

```bat
python bot.py
```
The script will automatically create `store.db` (SQLite) and the required tables on first start.

## Project Structure

```
TelegramStoreBot/
│   bot.py                # Main bot implementation (already provided)
│   requirements.txt      # Python dependencies
│   README.md             # This file
│   .gitignore           # Recommended ignore patterns
│   Images/               # Folder for product images (created at runtime)
│   store.db              # SQLite DB (generated automatically)
└───
```

## Notes & Tips

- The bot uses **environment variables** for the token to keep credentials out of source control.
- All images are stored under the `Images` directory relative to the script.
- If you need to reset the database, simply delete `store.db` and restart the bot.
- For production, consider running the bot with a process manager (e.g., `pm2` for Windows) and securing the token.

---

Enjoy building and extending your Telegram store! 🎉
