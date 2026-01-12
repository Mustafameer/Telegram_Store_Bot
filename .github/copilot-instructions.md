<!-- Copilot / AI agent instructions for contributors -->
# Repo-specific Copilot Instructions

Purpose: Quickly orient an AI coding agent to be productive in this repository.

- **Big picture**: This repo implements a Telegram-based e‑commerce bot (Python) plus a Flutter storefront app. The main bot runtime is in `bot.py`; the app lives under `flutter_store_app/`.

- **Primary entry points**:
  - Run the bot locally: `python bot.py` or use [start_bot.bat](start_bot.bat).
  - CI / cloud process: `Procfile` and [run_cloud.bat](run_cloud.bat) / [deploy_to_cloud.bat](deploy_to_cloud.bat).

- **Database behaviour (critical)**:
  - Local dev uses SQLite file under `data/` (see [bot.py](bot.py)).
  - If `DATABASE_URL` env var is set, the code switches to PostgreSQL (psycopg2). The code actively prefers Postgres in that mode and may remove the local DB file to avoid confusion.
  - DB helper modules:
    - high-level helpers: [db_manager.py](db_manager.py)
    - lower-level wrapper & migration logic embedded in [bot.py](bot.py)
  - Query pattern: source code uses `?` placeholders in queries and normalizes to `%s` for Postgres via `normalize_query` / `CursorWrapper`. When adding queries, follow the `?` placeholder style and let helpers convert for Postgres.

- **Models & mapping**:
  - Simple data models live in `integration_models.py`. Many DB helper functions return model instances (e.g., `get_seller_by_telegram`, `get_products`). Use those for consistent deserialization.

- **Images & seed data**:
  - Product images are stored at `data/Images` at runtime and seeded from `seed_data/Images` when present. When modifying image handling, update both locations.

- **Migrations & schema changes**:
  - Migration scripts: `apply_migration*.py`, `force_migration` command is also implemented in `bot.py` for cloud Postgres. Inspect these before changing schema.
  - Note: bot includes logic to ALTER column types (e.g., TelegramID → BIGINT) when running against Postgres — be conservative and test migrations on a copy.

- **Dependency & runtime notes**:
  - See [requirements.txt](requirements.txt) for runtime libs; `pyTelegramBotAPI`, `psycopg2-binary`, `python-dotenv` are important.
  - The token is read from `TELEGRAM_BOT_TOKEN` (preferred) or embedded during local testing; do not commit tokens.

- **Testing & conventions**:
  - Unit/quick tests follow `test_*.py` naming (examples: `test_local_pg.py`, `test_cloud_connection.py`). Use `python <testfile>.py` to run quick tests; no full test harness is present.
  - DB access in codebase uses either `db_manager` helpers or inline DB wrappers in `bot.py` — prefer `db_manager` for new helpers and maintain the `?` query style.

- **Common pitfalls to avoid**:
  - Don’t assume SQLite and Postgres are interchangeable: the code performs textual conversions (`DATETIME`→`TIMESTAMP`, `AUTOINCREMENT`→`SERIAL`) and placeholder changes; validate queries on both backends.
  - The bot may delete local DB when `DATABASE_URL` exists — be careful when running cloud-mode locally.

- **Where to look for examples**:
  - Main bot logic and DB wrapper: [bot.py](bot.py)
  - High-level DB helpers: [db_manager.py](db_manager.py)
  - Migration helpers & scripts: `apply_migration.py`, `apply_migration_direct.py`, `apply_migration_railway.py`
  - Start/deploy scripts: [start_bot.bat](start_bot.bat), [run_cloud.bat](run_cloud.bat), [deploy_to_cloud.bat](deploy_to_cloud.bat)

If anything in this summary is unclear or you'd like another section (examples for writing a new DB helper, a small migration example, or how to run the Flutter app), tell me which part to expand. 
