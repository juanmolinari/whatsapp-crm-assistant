from datetime import date

from app.services.calendar import handle_meeting_calendar
from app.services.parser import parse_text
from app.services.repository import save_parsed_input


def test_meeting_calendar_reports_detected_date_without_google(db_session):
    parsed = parse_text("Reunión con Cliente A mañana a las 10.", base_date=date(2026, 6, 28))
    raw = save_parsed_input(db_session, "test", "Reunión con Cliente A mañana a las 10.", parsed)

    result = handle_meeting_calendar(db_session, raw.id, parsed)

    assert result.attempted is True
    assert result.created is False
    assert "Fecha: 2026-06-29" in result.message
    assert "Hora: 10:00" in result.message


def test_meeting_calendar_asks_for_time_when_missing(db_session):
    parsed = parse_text("Reunión con Cliente A mañana.", base_date=date(2026, 6, 28))
    raw = save_parsed_input(db_session, "test", "Reunión con Cliente A mañana.", parsed)

    result = handle_meeting_calendar(db_session, raw.id, parsed)

    assert result.attempted is True
    assert result.created is False
    assert "falta la hora" in result.message
