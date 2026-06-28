from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app import models
from app.config import Settings, get_settings
from app.schemas import DetectedDate, ParsedMessage

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


@dataclass
class CalendarResult:
    attempted: bool
    created: bool
    message: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    event_id: str | None = None
    event_link: str | None = None


def handle_meeting_calendar(db: Session, raw_input_id: int, parsed: ParsedMessage) -> CalendarResult:
    settings = get_settings()
    if parsed.commercial_context.stage != "meeting_scheduled":
        return CalendarResult(attempted=False, created=False, message="")

    meeting_date = _first_meeting_date(parsed.dates_detected)
    if not meeting_date:
        return CalendarResult(
            attempted=True,
            created=False,
            message="Detecté una reunión, pero falta la fecha. Ej: 'mañana a las 10'.",
        )
    if not meeting_date.time:
        return CalendarResult(
            attempted=True,
            created=False,
            message=f"Detecté una reunión para {meeting_date.date}, pero falta la hora. Ej: 'a las 10'.",
        )

    start_at = _start_datetime(meeting_date, settings)
    end_at = start_at + timedelta(minutes=settings.default_meeting_duration_minutes)
    title = _event_title(parsed)
    description = parsed.summary

    if not settings.google_calendar_enabled:
        return CalendarResult(
            attempted=True,
            created=False,
            start_at=start_at,
            end_at=end_at,
            message=(
                "Detecté una reunión, pero Google Calendar no está habilitado.\n"
                f"Fecha: {start_at:%Y-%m-%d}\n"
                f"Hora: {start_at:%H:%M}\n"
                "Para crearla automáticamente, configurá GOOGLE_CALENDAR_ENABLED=true."
            ),
        )

    try:
        event = create_google_calendar_event(settings, title, description, start_at, end_at)
    except CalendarSetupError as exc:
        return CalendarResult(
            attempted=True,
            created=False,
            start_at=start_at,
            end_at=end_at,
            message=f"No pude crear el evento en Google Calendar: {exc}",
        )

    db.add(
        models.CalendarEvent(
            raw_input_id=raw_input_id,
            provider="google",
            provider_event_id=event.get("id"),
            title=title,
            start_at=start_at.replace(tzinfo=None),
            end_at=end_at.replace(tzinfo=None),
            status="created",
        )
    )
    db.commit()
    link = event.get("htmlLink")
    message = f"Reunión creada en Google Calendar.\nFecha: {start_at:%Y-%m-%d}\nHora: {start_at:%H:%M}"
    if link:
        message += f"\nLink: {link}"
    return CalendarResult(
        attempted=True,
        created=True,
        message=message,
        start_at=start_at,
        end_at=end_at,
        event_id=event.get("id"),
        event_link=link,
    )


class CalendarSetupError(RuntimeError):
    pass


def create_google_calendar_event(settings: Settings, title: str, description: str, start_at: datetime, end_at: datetime) -> dict:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarSetupError("faltan dependencias. Ejecutá: .\\.venv\\Scripts\\python.exe -m pip install -r requirements-google.txt") from exc

    credentials_path = Path(settings.google_calendar_credentials_path)
    token_path = Path(settings.google_calendar_token_path)
    if not credentials_path.exists():
        raise CalendarSetupError(f"falta el archivo {credentials_path}.")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    service = build("calendar", "v3", credentials=creds)
    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_at.isoformat(), "timeZone": settings.timezone},
        "end": {"dateTime": end_at.isoformat(), "timeZone": settings.timezone},
    }
    return service.events().insert(calendarId=settings.google_calendar_id, body=event_body).execute()


def _first_meeting_date(dates: list[DetectedDate]) -> DetectedDate | None:
    for item in dates:
        if item.meaning == "meeting":
            return item
    return dates[0] if dates else None


def _start_datetime(meeting_date: DetectedDate, settings: Settings) -> datetime:
    hour, minute = (int(part) for part in meeting_date.time.split(":", 1))
    day = datetime.fromisoformat(meeting_date.date).date()
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(settings.timezone))


def _event_title(parsed: ParsedMessage) -> str:
    target = parsed.client_alias or parsed.company_name
    return f"Reunión con {target}" if target else "Reunión comercial"
