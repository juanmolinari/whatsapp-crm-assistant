import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.services.telegram_bot import TelegramBot


def main() -> None:
    settings = get_settings()
    if not settings.telegram_enabled:
        print("TELEGRAM_ENABLED=false. Activá TELEGRAM_ENABLED=true en .env para correr el bot.")
        return
    init_db()
    bot = TelegramBot(settings=settings, db_factory=SessionLocal)
    bot.run_forever()


if __name__ == "__main__":
    main()
