import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app import models
from app.config import Settings
from app.services.calendar import handle_meeting_calendar
from app.services.commands import run_command
from app.services.excel import process_excel
from app.services.parser import parse_text
from app.services.repository import save_parsed_input
from app.services.transcription import transcribe_audio


class TelegramBotError(RuntimeError):
    pass


class TelegramBot:
    def __init__(self, settings: Settings, db_factory, client: httpx.Client | None = None):
        if not settings.telegram_bot_token:
            raise TelegramBotError("Falta TELEGRAM_BOT_TOKEN en .env.")
        self.settings = settings
        self.db_factory = db_factory
        self.client = client or httpx.Client(timeout=45)
        self.api_base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.file_base = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}"
        self.upload_dir = settings.storage_dir / "telegram"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def run_forever(self) -> None:
        offset: int | None = None
        print("Telegram bot activo. Mandá /start desde tu chat.")
        while True:
            try:
                updates = self.get_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    self.handle_update(update)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"Error en Telegram bot: {exc}")
                time.sleep(5)

    def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        data = self._post("getUpdates", payload)
        return data.get("result", [])

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not message:
            return
        chat_id = message["chat"]["id"]
        user_id = message.get("from", {}).get("id")
        if not is_authorized(user_id, self.settings.owner_telegram_user_id):
            self.send_message(
                chat_id,
                f"Usuario no autorizado. Tu Telegram user_id es {user_id}. "
                "Copialo en OWNER_TELEGRAM_USER_ID dentro de .env.",
            )
            return

        db = self.db_factory()
        try:
            response = self._handle_message(db, message)
            self.send_message(chat_id, response)
        finally:
            db.close()

    def _handle_message(self, db: Session, message: dict[str, Any]) -> str:
        if text := message.get("text"):
            return self._handle_text(db, text)
        if voice := message.get("voice"):
            return self._handle_file(db, voice["file_id"], "telegram_voice.ogg", "audio")
        if audio := message.get("audio"):
            return self._handle_file(db, audio["file_id"], audio.get("file_name") or "telegram_audio", "audio")
        if document := message.get("document"):
            return self._handle_file(db, document["file_id"], document.get("file_name") or "telegram_document", "document")
        return "Recibí el mensaje, pero todavía no sé procesar ese tipo de contenido."

    def _handle_text(self, db: Session, text: str) -> str:
        if text.startswith("/"):
            return run_command(db, text)
        parsed = parse_text(text)
        raw = save_parsed_input(db, "telegram_text", text, parsed)
        calendar_result = handle_meeting_calendar(db, raw.id, parsed)
        if calendar_result.attempted:
            return calendar_result.message
        task_count = len(parsed.tasks)
        review = " Sí, requiere revisión." if parsed.needs_review else ""
        return f"Guardado. Tipo: {parsed.message_type}. Tareas detectadas: {task_count}.{review}"

    def _handle_file(self, db: Session, file_id: str, filename: str, source_hint: str) -> str:
        stored = self.download_file(file_id, filename)
        suffix = stored.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            count = process_excel(db, stored)
            db.add(models.UploadedFile(filename=stored.name, stored_path=str(stored), content_type="telegram/document"))
            db.commit()
            return f"Excel procesado. Filas importadas: {count}."
        if source_hint == "audio" or suffix in {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".webm"}:
            transcript = transcribe_audio(stored)
            parsed = parse_text(transcript)
            raw = save_parsed_input(db, "telegram_audio", transcript, parsed)
            calendar_result = handle_meeting_calendar(db, raw.id, parsed)
            db.add(models.UploadedFile(raw_input_id=raw.id, filename=stored.name, stored_path=str(stored), content_type="telegram/audio"))
            db.commit()
            if calendar_result.attempted:
                return f"Audio transcripto: {transcript[:500]}\n\n{calendar_result.message}"
            return f"Audio guardado. Transcripción: {transcript[:700]}"
        text = f"Archivo recibido por Telegram: {stored.name}. Revisar manualmente."
        parsed = parse_text(text)
        raw = save_parsed_input(db, "telegram_document", text, parsed)
        db.add(models.UploadedFile(raw_input_id=raw.id, filename=stored.name, stored_path=str(stored), content_type="telegram/document"))
        db.commit()
        return "Documento guardado para revisión manual."

    def download_file(self, file_id: str, filename: str) -> Path:
        file_info = self._post("getFile", {"file_id": file_id})["result"]
        file_path = file_info["file_path"]
        suffix = Path(file_path).suffix or Path(filename).suffix
        safe_stem = Path(filename).stem or "telegram_file"
        destination = self._unique_path(self.upload_dir / f"{safe_stem}{suffix}")
        response = self.client.get(f"{self.file_base}/{file_path}")
        response.raise_for_status()
        destination.write_bytes(response.content)
        return destination

    def send_message(self, chat_id: int, text: str) -> None:
        chunks = split_telegram_text(text)
        for chunk in chunks:
            self._post("sendMessage", {"chat_id": chat_id, "text": chunk})

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(f"{self.api_base}/{method}", json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise TelegramBotError(data.get("description", f"Telegram API error in {method}"))
        return data

    @staticmethod
    def _unique_path(path: Path) -> Path:
        candidate = path
        counter = 1
        while candidate.exists():
            candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
            counter += 1
        return candidate


def is_authorized(user_id: int | None, configured_owner: str) -> bool:
    if not configured_owner.strip():
        return True
    return str(user_id) == configured_owner.strip()


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines():
        if len(current) + len(line) + 1 > limit:
            chunks.append(current.rstrip())
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current.rstrip())
    return chunks or [text[:limit]]
