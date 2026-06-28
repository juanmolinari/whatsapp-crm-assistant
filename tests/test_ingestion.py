from datetime import date

import pandas as pd

from app import models
from app.services.excel import process_excel
from app.services.parser import parse_text
from app.services.repository import save_parsed_input
from app.services.summary import generate_daily_summary, render_summary
from app.services.transcription import transcribe_audio
from app.services.zero_cost import CostBlockedError, assert_zero_cost_allowed


def test_save_parsed_input_creates_task(db_session):
    parsed = parse_text("Recordame llamar a Cliente A mañana.", base_date=date(2026, 6, 28))
    save_parsed_input(db_session, "manual_text", "Recordame llamar a Cliente A mañana.", parsed)

    assert db_session.query(models.RawInput).count() == 1
    assert db_session.query(models.Task).count() == 1
    assert db_session.query(models.ClientNote).count() == 1


def test_excel_processing_creates_records(db_session, tmp_path):
    path = tmp_path / "pipeline.xlsx"
    pd.DataFrame(
        [{"cliente": "Cliente C", "monto": "USD 500k", "etapa": "propuesta", "próximo paso": "Follow-up el viernes"}]
    ).to_excel(path, index=False)

    count = process_excel(db_session, path)

    assert count == 1
    assert db_session.query(models.RawInput).count() == 1
    assert db_session.query(models.Opportunity).count() == 1


def test_simulated_transcription_uses_sidecar(tmp_path):
    audio = tmp_path / "nota.wav"
    audio.write_bytes(b"fake")
    sidecar = tmp_path / "nota.wav.txt"
    sidecar.write_text("Cliente Audio. Llamar mañana.", encoding="utf-8")

    assert transcribe_audio(audio) == "Cliente Audio. Llamar mañana."


def test_daily_summary_is_generated(db_session):
    parsed = parse_text("Recordame llamar a Cliente A hoy.", base_date=date.today())
    save_parsed_input(db_session, "manual_text", "Recordame llamar a Cliente A hoy.", parsed)

    summary = generate_daily_summary(db_session, date.today())

    assert "Resumen diario" in summary.content
    assert "Follow-ups para hoy" in summary.content


def test_daily_summary_omits_empty_sections(db_session):
    summary = generate_daily_summary(db_session, date.today())

    assert "Resumen de ayer" not in summary.content
    assert "Oportunidades abiertas" not in summary.content
    assert "Riesgos o temas sin resolver" not in summary.content
    assert "Sin actividad registrada" in summary.content


def test_render_summary_only_includes_populated_sections(db_session):
    task = models.Task(description="Llamar para seguimiento", client_alias="Cliente A", due_date=date.today(), priority="medium")

    content = render_summary(date.today(), [], [], [], [task], [], [])

    assert "Follow-ups para hoy" in content
    assert "Cliente A: Llamar para seguimiento" in content
    assert "Resumen de ayer" not in content
    assert "Oportunidades abiertas" not in content
    assert "Riesgos o temas sin resolver" not in content


def test_zero_cost_blocks_whatsapp():
    try:
        assert_zero_cost_allowed("send_whatsapp")
    except CostBlockedError as exc:
        assert "STRICT_ZERO_COST=true" in str(exc)
    else:
        raise AssertionError("Expected zero-cost guard to block WhatsApp")
