import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.services.parser import today_local
from app.services.summary import generate_daily_summary


def job() -> None:
    db = SessionLocal()
    try:
        summary = generate_daily_summary(db, today_local())
        print(f"Resumen generado: {summary.summary_date}")
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    init_db()
    hour, minute = settings.daily_summary_time.split(":", 1)
    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(job, CronTrigger(hour=int(hour), minute=int(minute), timezone=settings.timezone))
    print(f"Scheduler activo. Resumen diario a las {settings.daily_summary_time} ({settings.timezone}).")
    scheduler.start()


if __name__ == "__main__":
    main()
