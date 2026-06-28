$ErrorActionPreference = "Stop"

if (Test-Path ".venv\Scripts\python.exe") {
  .\.venv\Scripts\python.exe scripts\run_telegram_bot.py
} else {
  python scripts\run_telegram_bot.py
}
