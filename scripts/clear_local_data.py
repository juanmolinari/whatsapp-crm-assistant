from pathlib import Path

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    for path in [Path(db_path), Path(db_path + "-shm"), Path(db_path + "-wal")]:
        if path.exists():
            path.unlink()
            print(f"Borrado: {path}")
    upload_dir = settings.storage_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    for item in upload_dir.iterdir():
        if item.name != ".gitkeep" and item.is_file():
            item.unlink()
            print(f"Borrado: {item}")


if __name__ == "__main__":
    main()
