import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db
from app.services.parser import today_local
from app.services.summary import generate_daily_summary


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        summary = generate_daily_summary(db, today_local())
        print(summary.content)
    finally:
        db.close()


if __name__ == "__main__":
    main()
